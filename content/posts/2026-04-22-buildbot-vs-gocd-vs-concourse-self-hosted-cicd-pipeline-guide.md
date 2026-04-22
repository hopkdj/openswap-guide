---
title: "Buildbot vs GoCD vs Concourse CI: Self-Hosted Pipeline Guide 2026"
date: 2026-04-22
tags: ["comparison", "guide", "self-hosted", "ci-cd", "devops"]
draft: false
description: "In-depth comparison of Buildbot, GoCD, and Concourse CI for self-hosted CI/CD pipelines. Includes Docker Compose configs, feature comparison, and deployment guides."
---

Self-hosted CI/CD pipelines give teams complete control over build infrastructure, data privacy, and cost. While Jenkins dominates the market, three powerful alternatives stand apart with fundamentally different design philosophies: **Buildbot** (Python-based, highly flexible), **GoCD** (value stream mapping, pipeline-as-code), and **Concourse CI** (container-native, pipeline-as-code purist).

This guide compares these three platforms in depth, with real Docker Compose configurations, live project stats, and practical deployment instructions.

## Why Self-Host Your CI/CD Pipeline

Running your own CI/CD infrastructure means you own the entire build pipeline — source code, artifacts, test results, and deployment credentials never leave your network. For organizations in regulated industries, teams working with proprietary codebases, or anyone who wants to avoid vendor lock-in and per-minute pricing, self-hosted CI/CD is the only way to maintain full sovereignty.

Compared to cloud-hosted alternatives, self-hosted pipelines offer:

- **No per-minute billing** — unlimited builds at hardware cost
- **Full data privacy** — source code and artifacts stay on your infrastructure
- **Custom executors** — run builds on any hardware, GPU clusters, or isolated networks
- **No rate limits** — queue as many parallel jobs as your hardware supports
- **Air-gapped builds** — compile and test in fully offline environments

## Buildbot CI — The Python-Powered Veteran

**GitHub:** [buildbot/buildbot](https://github.com/buildbot/buildbot) | **Stars:** 5,450 | **Language:** Python | **Last Updated:** April 2026

Buildbot is one of the oldest open-source CI frameworks still actively maintained. Originally created by Brian Warner in 2003, it has evolved into a mature, Python-based platform used by projects like Mozilla, Chromium, and the FreeBSD project.

### Architecture

Buildbot uses a master-worker architecture:

- **Buildbot Master** — the central coordinator that schedules builds, manages the web UI, and stores build state
- **Buildbot Workers** — lightweight agents that execute build steps on various platforms (Linux, Windows, macOS, BSD)
- **Schedulers** — trigger builds based on source control changes, timers, or manual requests
- **Change Sources** — poll or receive webhooks from Git, GitHub, GitLab, SVN, and other version control systems

The entire configuration lives in a single Python file (`master.cfg`), giving you the full power of Python to define complex build logic, conditional steps, and dynamic worker assignment.

### Key Features

- **Python-native configuration** — write build pipelines in plain Python, no custom DSL required
- **Multi-language worker support** — workers run on any OS, including Windows and macOS
- **Flexible schedulers** — force schedulers, timed schedulers, try schedulers, and change-based triggers
- **Extensible reporting** — email, IRC, Gerrit, GitHub status, Slack, and custom reporters
- **Virtual builder support** — dynamically create builders based on build parameters
- **Waterfall and Grid views** — visual build status dashboards

### Docker Deployment

Buildbot publishes official Docker images for both master and worker. A minimal production deployment:

```yaml
version: "3.8"
services:
  master:
    image: buildbot/buildbot-master:latest
    ports:
      - "8010:8010"   # Web UI
      - "9989:9989"   # Worker port
    volumes:
      - ./master.cfg:/srv/buildbot/master.cfg:ro
      - buildbot-data:/srv/buildbot
    environment:
      - BUILDBOT_CONFIG_URL=file:///srv/buildbot/master.cfg
    restart: unless-stopped

  worker1:
    image: buildbot/buildbot-worker:latest
    depends_on:
      - master
    environment:
      - BUILDMASTER=master
      - BUILDMASTER_PORT=9989
      - WORKERNAME=worker1
      - WORKERPASS=pass
    volumes:
      - worker1-data:/srv/buildbot
    restart: unless-stopped

volumes:
  buildbot-data:
  worker1-data:
```

To configure the master, mount a `master.cfg` file. A minimal configuration looks like this:

```python
from buildbot.plugins import util, changes, schedulers, steps, reporters

c = BuildmasterConfig = {}

# Workers
c['workers'] = [util.Worker("worker1", "pass")]

# Source control
c['change_source'] = [changes.GitPoller(
    'https://github.com/your-org/your-repo.git',
    workdir='gitpoller-workdir',
    branch='main',
    pollinterval=300
)]

# Scheduler
c['schedulers'] = [schedulers.SingleBranchScheduler(
    name="main",
    change_filter=util.ChangeFilter(branch='main'),
    treeStableTimer=30,
    builderNames=["runtests"]
)]

# Builder
factory = util.BuildFactory()
factory.addStep(steps.Git(repourl='https://github.com/your-org/your-repo.git', mode='incremental'))
factory.addStep(steps.ShellCommand(command=["make", "test"]))

c['builders'] = [util.BuilderConfig(
    name="runtests",
    workernames=["worker1"],
    factory=factory
)]

# Web UI
c['www'] = dict(port=8010, plugins=dict(waterfall_view={}, console_view={}))
c['db'] = {'db_url': 'sqlite:///state.sqlite'}
```

Buildbot's greatest strength is its flexibility. Because configuration is pure Python, you can implement arbitrarily complex build logic — conditional step execution, dynamic worker selection, parameterized builds, and integration with any Python library.

## GoCD — Value Stream Mapping for Continuous Delivery

**GitHub:** [gocd/gocd](https://github.com/gocd/gocd) | **Stars:** 7,389 | **Language:** Java | **Last Updated:** April 2026

GoCD, originally developed by ThoughtWorks, is designed specifically for modeling complex continuous delivery pipelines. Its standout feature is the **Value Stream Map (VSM)** — a visual representation of the entire delivery pipeline from code commit to production deployment.

### Architecture

GoCD uses a server-agent architecture:

- **GoCD Server** — central orchestrator with web UI, pipeline management, and artifact storage
- **GoCD Agents** — elastic build agents that execute pipeline stages. Agents auto-register and can be scaled horizontally
- **Pipeline Configuration** — defined via XML or the modern [Pipeline-as-Code](https://github.com/gocd/gocd) YAML format using `.gocd.yaml` files stored in your repository

### Key Features

- **Value Stream Map** — visualize the entire pipeline from commit to deployment in one view
- **Fan-in/Fan-out pipelines** — model complex dependency graphs with parallel stages and gated promotions
- **Environment management** — assign agents to specific environments (dev, staging, production) with approval gates
- **Plugin ecosystem** — 100+ community plugins for notifications, artifacts, auth, and more
- **Elastic agents** — dynamically provision agents on Docker, Kubernetes, or cloud providers
- **Audit trail** — complete history of who changed what in the pipeline and when

### Docker Deployment

GoCD provides official Docker images. A minimal server-agent setup:

```yaml
version: "3.8"
services:
  server:
    image: gocd/gocd-server:v24.5.0
    ports:
      - "8153:8153"   # HTTP
      - "8154:8154"   # HTTPS
    volumes:
      - gocd-server:/godata
      - gocd-artifacts:/home/go/.gocd
    environment:
      - GOCD_SERVER_JVM_OPTS=-Xmx4g -Xms2g
    restart: unless-stopped

  agent1:
    image: gocd/gocd-agent-ubuntu-22.04:v24.5.0
    depends_on:
      - server
    environment:
      - GO_SERVER_URL=https://server:8154/go
      - AGENT_AUTO_REGISTER_KEY=your-auto-register-key
    volumes:
      - gocd-agent1:/home/go
    restart: unless-stopped

volumes:
  gocd-server:
  gocd-artifacts:
  gocd-agent1:
```

After starting the server, configure pipelines via the web UI at `http://localhost:8153` or use Pipeline-as-Code by committing `.gocd.yaml` files to your repository:

```yaml
format_version: 10
pipelines:
  build-and-test:
    group: defaultGroup
    materials:
      repo:
        git: https://github.com/your-org/your-repo.git
        branch: main
    stages:
      - build:
          jobs:
            compile:
              tasks:
                - exec:
                    command: make
                    arguments: [build]
      - test:
          jobs:
            unit-tests:
              tasks:
                - exec:
                    command: make
                    arguments: [test]
          approval:
            type: success
```

GoCD's VSM is particularly valuable for teams practicing continuous delivery. The visual pipeline view makes it easy to identify bottlenecks, track deployment lead times, and understand dependencies between stages.

## Concourse CI — Container-Native Pipeline Engine

**GitHub:** [concourse/concourse](https://github.com/concourse/concourse) | **Stars:** 7,819 | **Language:** Go | **Last Updated:** April 2026

Concourse CI takes a radically different approach to CI/CD. Built by Pivotal (now VMware) and now maintained as a community project, it treats every build step as an isolated container and every pipeline as a directed acyclic graph (DAG) of resources and jobs.

### Architecture

Concourse has a three-tier architecture:

- **Web Node** — serves the UI, API, and handles authentication. Coordinates pipeline scheduling
- **Worker Node** — runs containers (via Garden or containerd) for each build task. Workers are stateless and can be added or removed dynamically
- **PostgreSQL** — stores pipeline configurations, build state, and resource version history

Pipelines are defined declaratively in YAML using a unique resource/job/task model:

- **Resources** — inputs and outputs (Git repos, Docker images, S3 buckets, PRs)
- **Jobs** — sequences of tasks that consume and produce resources
- **Tasks** — individual steps that run inside isolated containers

### Key Features

- **Container isolation** — every task runs in its own container with no shared state
- **Immutable infrastructure** — builds are reproducible because containers start from clean images each time
- **Resource versioning** — track every version of every input (git commit, image digest, S3 object)
- **Pipeline-as-code** — pipelines are YAML files, versioned alongside your application
- **Fly CLI** — manage pipelines, trigger builds, and view outputs from the command line
- **Time-based triggers** — schedule builds with the `time` resource

### Docker Compose Deployment

Concourse provides an official `docker-compose.yml` for development and testing:

```yaml
version: "3.8"
services:
  db:
    image: postgres:17
    shm_size: 1gb
    ports:
      - "6543:5432"
    environment:
      POSTGRES_DB: concourse
      POSTGRES_USER: concourse
      POSTGRES_PASSWORD: changeme
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U concourse -d concourse"]
      interval: 3s
      timeout: 3s
      retries: 5

  web:
    image: concourse/concourse:latest
    command: web
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "8080:8080"
    volumes:
      - ./keys:/concourse-keys
    environment:
      CONCOURSE_SESSION_SIGNING_KEY: /concourse-keys/session_signing_key
      CONCOURSE_TSA_AUTHORIZED_KEYS: /concourse-keys/authorized_worker_keys
      CONCOURSE_TSA_HOST_KEY: /concourse-keys/tsa_host_key
      CONCOURSE_LOG_LEVEL: info
      CONCOURSE_POSTGRES_HOST: db
      CONCOURSE_POSTGRES_USER: concourse
      CONCOURSE_POSTGRES_PASSWORD: changeme
      CONCOURSE_POSTGRES_DATABASE: concourse
      CONCOURSE_EXTERNAL_URL: http://localhost:8080
      CONCOURSE_ADD_LOCAL_USER: admin:admin
      CONCOURSE_MAIN_TEAM_LOCAL_USER: admin

  worker:
    image: concourse/concourse:latest
    command: worker
    depends_on:
      - web
    privileged: true
    volumes:
      - ./keys:/concourse-keys
    environment:
      CONCOURSE_TSA_HOST: web:2222
      CONCOURSE_TSA_PUBLIC_KEY: /concourse-keys/tsa_host_key.pub
      CONCOURSE_TSA_WORKER_PRIVATE_KEY: /concourse-keys/worker_key
```

Generate the required SSH keys before starting:

```bash
mkdir -p keys
ssh-keygen -t rsa -f ./keys/web_rsa -N ''
ssh-keygen -t rsa -f ./keys/worker_key -N ''
ssh-keygen -t rsa -f ./keys/session_signing_key -N ''
# Combine worker public keys
cat ./keys/worker_key.pub > ./keys/authorized_worker_keys
```

Define pipelines using the `fly` CLI:

```bash
# Login
fly -t main login -c http://localhost:8080 -u admin -p admin

# Set pipeline
fly -t main set-pipeline -p my-app -c pipeline.yml

# Unpause and trigger
fly -t main unpause-pipeline -p my-app
fly -t main trigger-job -j my-app/build
```

Example pipeline definition:

```yaml
resources:
  - name: source-code
    type: git
    source:
      uri: https://github.com/your-org/your-repo.git
      branch: main

  - name: every-6-hours
    type: time
    source:
      interval: 6h

jobs:
  - name: build-and-test
    plan:
      - get: source-code
        trigger: true
      - get: every-6-hours
        trigger: true
      - task: compile
        file: source-code/ci/compile.yml
      - task: test
        file: source-code/ci/test.yml
      - put: docker-image
        params:
          build: source-code
```

Concourse's strict container isolation means builds are highly reproducible. However, this also means every task must explicitly declare all inputs — there is no implicit shared filesystem between steps.

## Comparison Table

| Feature | Buildbot | GoCD | Concourse CI |
|---|---|---|---|
| **Language** | Python | Java | Go |
| **GitHub Stars** | 5,450 | 7,389 | 7,819 |
| **Pipeline Format** | Python (`master.cfg`) | YAML/XML (`.gocd.yaml`) | YAML (pipeline files) |
| **Execution Model** | Master-Worker | Server-Agent | Web-Worker (container-per-task) |
| **Build Isolation** | Process-level | Process-level | Container-level (isolated) |
| **Configuration Language** | Full Python | Declarative YAML | Declarative YAML |
| **Value Stream Map** | No | **Yes** (built-in) | No |
| **Fan-in/Fan-out** | Via triggers | **Native** (via materials) | Via `passed` constraints |
| **Dynamic Workers** | Manual | Elastic agents | Auto-scaling worker pools |
| **Resource Versioning** | Basic (SCM only) | Per-material | **Full** (all resources tracked) |
| **Web UI** | Waterfall, Grid, Console | VSM, Pipeline Dashboard | DAG View, Build Log |
| **CLI Tool** | `buildbot` | `gocd` (limited) | `fly` (full-featured) |
| **Docker Support** | Official images | Official images | Official images + compose |
| **Learning Curve** | Moderate (Python knowledge) | Low-Moderate | Moderate (resource model) |
| **Best For** | Complex custom logic, multi-OS | Enterprise CD, audit trails | Reproducible builds, container-native |

## Choosing the Right Platform

### Choose Buildbot if:
- You need **maximum flexibility** in build configuration (Python gives you unlimited power)
- Your builds run on **heterogeneous platforms** (Windows, macOS, Linux, embedded)
- You have complex, **conditional build logic** that a declarative format cannot express
- Your team is already comfortable with Python

Buildbot's configuration-as-Python is its greatest differentiator. While other tools require learning a custom DSL, Buildbot lets you write build pipelines using a language your developers already know.

### Choose GoCD if:
- You practice **continuous delivery** and need visual pipeline management
- Your organization requires **audit trails** and compliance documentation
- You have **complex deployment pipelines** with multiple environments and approval gates
- You want the **Value Stream Map** to identify bottlenecks in your delivery process

GoCD's fan-in/fan-out pipeline model excels at representing real-world CD workflows where code flows through multiple stages, environments, and quality gates before reaching production.

### Choose Concourse CI if:
- You want **strictly reproducible builds** with full container isolation
- Your team values **declarative pipeline-as-code** over imperative configuration
- You need **resource versioning** across all inputs (not just source code)
- You're running in a **container-native** environment (Kubernetes, containerd)

Concourse's resource model — where every input is versioned and every task is isolated — makes it the best choice for teams prioritizing build reproducibility and supply chain security.

## Performance and Resource Requirements

| Metric | Buildbot | GoCD | Concourse CI |
|---|---|---|---|
| **Server RAM** | 1-2 GB | 4+ GB (JVM) | 2-4 GB |
| **Worker RAM** | 512 MB+ | 2+ GB per agent | 2+ GB per worker |
| **Database** | SQLite/PostgreSQL | Built-in H2 or PostgreSQL | PostgreSQL (required) |
| **Startup Time** | ~5 seconds | ~30 seconds | ~15 seconds |
| **Disk (server)** | 5-10 GB | 20+ GB (artifacts) | 10-20 GB |
| **Horizontal Scaling** | Add workers | Add agents | Add workers |

GoCD has the highest resource overhead due to the JVM. Buildbot is the lightest on server resources. Concourse sits in the middle but requires PostgreSQL as an external dependency.

## Migration Considerations

If you are migrating from Jenkins or another CI system:

- **From Jenkins to Buildbot**: The Python configuration model is the closest to Jenkinsfile scripted pipelines. Use the `buildbot.plugins.steps.ShellCommand` step to replicate shell-based build steps.
- **From Jenkins to GoCD**: GoCD's pipeline-as-code YAML is similar to Jenkins declarative pipelines. The VSM provides better visualization than Jenkins Blue Ocean.
- **From Jenkins to Concourse**: Concourse requires the most mindset shift. Each task must be containerized, and shared state between steps must be explicit via resources. However, the payoff is fully reproducible builds.

## Related Reading

For teams evaluating the full CI/CD landscape, check out our [Woodpecker CI vs Drone CI vs Gitea Actions guide](../woodpecker-ci-vs-drone-ci-vs-gitea-actions-self-hosted-cicd-guide-2026/) for lightweight alternatives, or the [Tekton vs Argo Workflows vs Jenkins X comparison](../tekton-vs-argo-workflows-vs-jenkins-x-self-hosted-kubernetes-native-cicd-guide-2026/) for Kubernetes-native options. If you need self-hosted CI runners specifically, our [GitHub Actions Runner vs GitLab Runner vs Woodpecker article](../github-actions-runner-vs-gitlab-runner-vs-woodpecker-self-hosted-ci-agents-2026/) covers that comparison.

## FAQ

### Which CI platform is easiest to set up with Docker?

Concourse CI has the most complete out-of-the-box Docker experience. Its official `docker-compose.yml` includes web node, worker, and PostgreSQL in a single file. Buildbot and GoCD also have official Docker images but require slightly more manual configuration for multi-worker setups.

### Can Buildbot run builds on Windows and macOS?

Yes. Buildbot workers are cross-platform and run on Windows, macOS, Linux, and BSD. This makes it the best choice for projects that need to build and test on multiple operating systems simultaneously.

### Does GoCD support pipeline-as-code?

Yes. GoCD supports Pipeline-as-Code via `.gocd.yaml` files stored in your Git repository. You define pipelines declaratively in YAML and commit them alongside your application code. GoCD also supports the older XML-based configuration via the web UI.

### How does Concourse handle secrets and credentials?

Concourse supports parameterized pipelines with `((variable))` syntax. Secrets can be injected via CredHub, HashiCorp Vault, AWS Secrets Manager, or Concourse's own credential manager. Each pipeline can reference secrets without exposing them in the pipeline definition.

### Can I run multiple pipelines in parallel on GoCD?

Yes. GoCD agents can be configured with the number of concurrent jobs they can run. The server distributes jobs across available agents, and you can assign specific agents to environments or pipeline groups for isolation.

### Which platform has the best community support?

All three projects are actively maintained. Concourse CI has the largest GitHub star count (7,819) and the most active issue tracker. Buildbot has the longest track record with contributors from major open-source projects. GoCD is backed by ThoughtWorks and has an active plugin ecosystem.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Buildbot vs GoCD vs Concourse CI: Self-Hosted Pipeline Guide 2026",
  "description": "In-depth comparison of Buildbot, GoCD, and Concourse CI for self-hosted CI/CD pipelines. Includes Docker Compose configs, feature comparison, and deployment guides.",
  "datePublished": "2026-04-22",
  "dateModified": "2026-04-22",
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
