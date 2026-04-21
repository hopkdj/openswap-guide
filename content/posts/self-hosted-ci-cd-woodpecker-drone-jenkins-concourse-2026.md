---
title: "Best Self-Hosted CI/CD Platforms: Woodpecker vs Drone vs Jenkins vs Concourse 2026"
date: 2026-04-14
tags: ["comparison", "guide", "self-hosted", "cicd", "devops"]
draft: false
description: "Complete comparison of self-hosted CI/CD platforms in 2026 — Woodpecker CI, Drone, Jenkins, and Concourse CI. Installation guides, feature comparison, and recommendations for every team size."
---

Continuous Integration and Continuous Deployment (CI/CD) pipelines are the backbone of modern software delivery. While cloud-hosted solutions like GitHub Actions and GitLab CI are convenient, many organizations need full control over their build infrastructure — whether for compliance, cost optimization, air-gapped environments, or avoiding vendor lock-in.

Self-hosted CI/CD platforms give you complete ownership of your build infrastructure. You choose where builds run, how secrets are managed, and who has access to your pipeline data. In this guide, we compare four mature open-source CI/CD platforms: **Woodpecker CI**, **Drone**, **Jenkins**, and **Concourse CI**.

## Why Self-Host Your CI/CD Platform?

Running your own CI/CD infrastructure offers several concrete advantages over cloud-hosted alternatives:

- **Cost predictability**: Cloud CI/CD charges per-minute of build time. With self-hosted runners on your own hardware or cheap spot instances, your cost per build drops dramatically as volume scales. Teams running thousands of builds per month often save 60-80% compared to cloud alternatives.
- **Data sovereignty**: Build logs, artifact caches, and environment variables often contain sensitive information. Self-hosting keeps everything within your network boundary, simplifying compliance with SOC 2, HIPAA, and GDPR requirements.
- **No vendor lock-in**: Cloud CI/CD platforms gradually entrench you with proprietary syntax, marketplace dependencies, and platform-specific features. Self-hosted tools based on open standards ([docker](https://www.docker.com/) containers, YAML pipelines) let you migrate between code forges freely.
- **Custom infrastructure**: Need GPUs for ML model training? Specialized hardware for embedded compilation? GPU passthrough in self-hosted runners is straightforward, while cloud CI/CD either lacks support or charges premium rates.
- **Offline and air-gapped builds**: Some environments cannot connect to external services. Self-hosted CI/CD works entirely on-premises with zero external dependencies.
- **Fine-grained access control**: Control exactly who can trigger builds, approve deployments, and access secrets — integrated with your existing LDAP, OIDC, or SAML infrastructure.

## 1. Woodpecker CI — Lightweight and Modern

Woodpecker CI is a community-driven fork of Drone CI that emphasizes simplicity, container-native pipelines, and active development. It has become one of the fastest-growing self-hosted CI/CD platforms thanks to its clean architecture and straightforward configuration.

### Architecture

Woodpecker uses a server-agent model. The server handles Git webhooks, UI, and pipeline scheduling. Workers (agents) execute pipeline steps inside Docker containers. A single server can distribute work across multiple agents, enabling horizontal scaling.

Key architectural decisions:
- Pipeline definitions live in `.woodpecker.yaml` at the repository root
- Each pipeline step runs in an isolated Docker container
- Shared state between steps uses workspace volumes
- Native integration with Gitea, Forgejo, GitHub, GitLab, Bitbucket, and Gogs

### Installation

The fastest way to get Woodpecker running is with Docker Compose. Here is a production-ready setup with a single worker:

```yaml
version: "3"

services:
  woodpecker-server:
    image: woodpeckerci/woodpecker-server:latest
    ports:
      - "8000:8000"
    volumes:
      - woodpecker-data:/var/lib/woodpecker
    environment:
      - WOODPECKER_OPEN=true
      - WOODPECKER_HOST=http://ci.example.com:8000
      - WOODPECKER_GITEA=true
      - WOODPECKER_GITEA_URL=https://gitea.example.com
      - WOODPECKER_GITEA_CLIENT=your-client-id
      - WOODPECKER_GITEA_SECRET=your-client-secret
      - WOODPECKER_AGENT_SECRET=your-agent-secret
    restart: unless-stopped

  woodpecker-agent:
    image: woodpeckerci/woodpecker-agent:latest
    command: agent
    depends_on:
      - woodpecker-server
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - WOODPECKER_SERVER=woodpecker-server:9000
      - WOODPECKER_AGENT_SECRET=your-agent-secret
    restart: unless-stopped

volumes:
  woodpecker-data:
```

After starting the stack with `docker compose up -d`, create an OAuth application in your Git forge pointing to `http://ci.example.com:8000/authorize` and fill in the client credentials.

### Pipeline Example

A typical `.woodpecker.yaml` for a Go project with testing and Docker image publishing:

```yaml
steps:
  test:
    image: golang:1.22
    commands:
      - go mod download
      - go vet ./...
      - go test -race -coverprofile=coverage.out ./...

  lint:
    image: golangci/golangci-lint:latest
    commands:
      - golangci-lint run

  build:
    image: plugins/docker
    settings:
      repo: registry.example.com/myapp
      tags: [latest, "${CI_COMMIT_TAG}"]
      registry: registry.example.com
      username:
        from_secret: registry_user
      password:
        from_secret: registry_pass
    when:
      branch: main
      event: [push, tag]
```

### Strengths and Weaknesses

**Strengths:**
- Extremely fast startup — server and agent each under 50 MB
- Active community with regular releases and responsive maintainers
- Clean, modern web UI w[kubernetes](https://kubernetes.io/)ime build logs
- Kubernetes agent support for running steps as pods instead of Docker containers
- Matrix builds for testing across multiple environments in parallel
- Built-in approval gates for production deployments
- Supports both Docker-in-Docker and rootless execution modes

**Weaknesses:**
- Smaller plugin ecosystem compared to Jenkins
- No built-in artifact storage — requires external S3 or similar backend
- Less mature for com[plex](https://www.plex.tv/) multi-repository pipeline orchestration
- Limited built-in reporting dashboards

## 2. Drone — The Original Container-Native CI

Drone pioneered the container-first CI/CD approach and remains a popular choice, especially in enterprise environments that value stability and long-term support.

### Architecture

Drone shares conceptual DNA with Woodpecker (since Woodpecker was forked from it) but has evolved along a different path. Drone uses a similar server-runner architecture with YAML-defined pipelines. Each step executes in an isolated container, and the platform emphasizes a plugin marketplace for extensibility.

Drone's plugin system is particularly well-developed. Plugins are simply Docker containers with defined input/output contracts, making them easy to write in any language. The official plugin repository includes integrations for Slack, email, S3, Kubernetes, Helm, SSH deploy, and dozens more.

### Installation

```yaml
version: "3"

services:
  drone-server:
    image: drone/drone:2
    ports:
      - "8000:80"
    volumes:
      - drone-data:/data
      - /var/lib/drone:/var/lib/drone
    environment:
      - DRONE_SERVER_HOST=ci.example.com
      - DRONE_SERVER_PROTO=https
      - DRONE_RPC_SECRET=super-duper-secret
      - DRONE_GITHUB_CLIENT_ID=your-client-id
      - DRONE_GITHUB_CLIENT_SECRET=your-client-secret
      - DRONE_GIT_ALWAYS_AUTH=false
    restart: unless-stopped

  drone-runner:
    image: drone/drone-runner-docker:1
    ports:
      - "3000:3000"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - DRONE_RPC_PROTO=http
      - DRONE_RPC_HOST=drone-server
      - DRONE_RPC_SECRET=super-duper-secret
      - DRONE_RUNNER_CAPACITY=2
      - DRONE_RUNNER_NAME=runner-1
    restart: unless-stopped

volumes:
  drone-data:
```

### Pipeline Example

Drone pipelines use a slightly different YAML structure with a top-level `kind: pipeline`:

```yaml
kind: pipeline
type: docker
name: default

steps:
  - name: test
    image: node:20
    commands:
      - npm ci
      - npm test
      - npm run build

  - name: deploy
    image: appleboy/drone-ssh
    settings:
      host: production.example.com
      username: deploy
      key:
        from_secret: ssh_key
      script:
        - cd /opt/app
        - docker compose pull
        - docker compose up -d
    when:
      branch: main
      status: success
```

### Strengths and Weaknesses

**Strengths:**
- Mature, battle-tested platform used by thousands of organizations
- Rich plugin marketplace with hundreds of pre-built integrations
- Enterprise support available through Harness (commercial backing)
- Multi-runner types: Docker, Kubernetes, Exec (bare metal)
- Built-in secret management with per-repository and global scopes
- Pipeline cloning and templating for reusing common steps across repos
- Strong security model with signed RPC communication between server and runners

**Weaknesses:**
- Development pace has slowed since the Harness acquisition
- Community fork (Woodpecker) has more momentum for open-source features
- Free tier limited to 5 concurrent pipelines for the commercial version
- YAML syntax is less intuitive than Woodpecker's step-based approach
- Web UI is functional but feels dated compared to modern alternatives

## 3. Jenkins — The Veteran Powerhouse

Jenkins has been the dominant self-hosted CI/CD platform for nearly two decades. With over 1,800 plugins and a massive ecosystem, Jenkins can handle virtually any build workflow imaginable.

### Architecture

Jenkins uses a controller-agent architecture. The controller (formerly "master") manages job configuration, scheduling, and the web UI. Agents (formerly "slaves") execute build steps and can run on any platform — Linux, Windows, macOS, or inside containers.

Unlike Woodpecker and Drone, Jenkins is not container-native by design. Pipeline steps can run on any connected agent, giving you the flexibility to mix bare metal, VMs, and containers in a single pipeline. This flexibility comes at the cost of complexity — Jenkins requires more infrastructure knowledge to operate effectively.

### Installation

Running Jenkins with Docker is straightforward, but a production setup typically includes a reverse proxy, persistent storage, and dedicated agents:

```yaml
version: "3"

services:
  jenkins:
    image: jenkins/jenkins:lts-jdk17
    ports:
      - "8080:8080"
      - "50000:50000"
    volumes:
      - jenkins-home:/var/jenkins_home
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - JAVA_OPTS=-Djenkins.install.runSetupWizard=false
      - JENKINS_ADMIN_ID=admin
      - JENKINS_ADMIN_PASSWORD=change-me
    restart: unless-stopped

volumes:
  jenkins-home:
```

After initial startup, Jenkins presents a setup wizard. For automated provisioning, pre-configure the `jenkins-home` volume with:
- `plugins.txt` listing required plugins
- `init.groovy.d/` scripts for security realm configuration
- `jobs/` directory with pre-configured pipeline definitions

### Pipeline Example

Jenkins uses its own Groovy-based Pipeline DSL (Declarative or Scripted syntax):

```groovy
pipeline {
    agent any

    environment {
        REGISTRY = credentials('docker-registry')
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Test') {
            parallel {
                stage('Unit Tests') {
                    agent { docker 'node:20' }
                    steps {
                        sh 'npm ci && npm test'
                    }
                }
                stage('Lint') {
                    agent { docker 'node:20' }
                    steps {
                        sh 'npm ci && npm run lint'
                    }
                }
            }
        }

        stage('Build Image') {
            agent any
            steps {
                script {
                    docker.build("myapp:${env.BUILD_NUMBER}")
                }
            }
        }

        stage('Push') {
            when {
                branch 'main'
            }
            steps {
                script {
                    docker.withRegistry('https://registry.example.com', 'docker-registry') {
                        docker.image("myapp:${env.BUILD_NUMBER}").push()
                        docker.image("myapp:${env.BUILD_NUMBER}").push('latest')
                    }
                }
            }
        }

        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                input message: 'Deploy to production?', ok: 'Deploy'
                sh 'kubectl apply -f k8s/production/'
            }
        }
    }

    post {
        always {
            cleanWs()
        }
        failure {
            mail to: 'team@example.com',
                 subject: "Build Failed: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                 body: "Check ${env.BUILD_URL}"
        }
    }
}
```

### Strengths and Weaknesses

**Strengths:**
- Largest plugin ecosystem of any CI/CD platform — 1,800+ plugins
- Supports every programming language, build system, and deployment target
- Declarative and Scripted pipeline DSL with full Groovy power
- Shared Libraries enable reusable pipeline code across hundreds of repositories
- Extremely flexible agent configuration — Docker, SSH, JNLP, Kubernetes, cloud APIs
- Blue Ocean UI provides a modern pipeline visualization layer
- Massive community — virtually every problem has a documented solution
- Backwards compatibility ensures pipelines written years ago still work

**Weaknesses:**
- Significant operational overhead — plugin updates frequently cause conflicts
- Groovy pipeline syntax has a steep learning curve compared to YAML
- Resource-heavy — the controller requires 4+ GB RAM for moderate workloads
- Plugin dependency chains can become unmaintained or incompatible
- Security surface area is large — each plugin is a potential vulnerability
- Build performance degrades without careful tuning of executors and workspaces
- Migration between Jenkins versions occasionally requires manual intervention

## 4. Concourse CI — Pipeline-as-Code Purist

Concourse CI takes a radically different approach to CI/CD. Built by Pivotal (now VMware) and now maintained by the open-source community, Concourse treats pipelines as first-class resources with a focus on reproducibility and immutability.

### Architecture

Concourse uses a three-component architecture:

1. **ATC (Air Traffic Control)**: The central coordinator — handles the web UI, API, scheduling, and build tracking
2. **Workers**: Execute tasks in isolated containers using Garden (a container runtime)
3. **PostgreSQL**: Stores all pipeline state, build history, and resource versions

Concourse's key innovation is its **resource** abstraction. Resources represent external systems — Git repositories, S3 buckets, Docker images, SemVer version trackers. Pipeline steps consume and produce resources, creating a declarative graph of dependencies. Every build is fully reproducible because Concourse tracks the exact version of every input resource.

### Installation

Concourse requires PostgreSQL and uses Docker Compose for the simplest deployment:

```yaml
version: "3"

services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: concourse
      POSTGRES_PASSWORD: concourse_pass
    volumes:
      - db-data:/var/lib/postgresql/data

  concourse:
    image: concourse/concourse:7.11
    command: quickstart
    depends_on:
      - db
    ports:
      - "8080:8080"
    environment:
      CONCOURSE_POSTGRES_HOST: db
      CONCOURSE_POSTGRES_USER: postgres
      CONCOURSE_POSTGRES_PASSWORD: concourse_pass
      CONCOURSE_POSTGRES_DATABASE: concourse
      CONCOURSE_EXTERNAL_URL: http://ci.example.com:8080
      CONCOURSE_ADD_LOCAL_USER: admin:admin
      CONCOURSE_MAIN_TEAM: local-user:admin
      CONCOURSE_WORKER_BAGGAGECLAIM_DRIVER: overlay
      CONCOURSE_CLIENT_SECRET: Y29uY291cnNlLXdlYgo=
      CONCOURSE_TSA_CLIENT_SECRET: Y29uY291cnNlLXdvcmtlcgo=
      CONCOURSE_X_FRAME_OPTIONS: allow
      CONCOURSE_CONTENT_SECURITY_POLICY: "*"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    privileged: true

volumes:
  db-data:
```

### Pipeline Example

Concourse pipelines are defined in YAML and applied via the `fly` CLI:

```yaml
resources:
  - name: source-code
    type: git
    source:
      uri: https://github.com/example/myapp.git
      branch: main

  - name: app-image
    type: docker-image
    source:
      repository: registry.example.com/myapp
      username: ((registry-user))
      password: ((registry-pass))

jobs:
  - name: test-and-build
    plan:
      - get: source-code
        trigger: true

      - task: run-tests
        config:
          platform: linux
          image_resource:
            type: docker-image
            source:
              repository: node
              tag: "20"
          inputs:
            - name: source-code
          run:
            path: sh
            args:
              - -c
              - |
                cd source-code
                npm ci
                npm test
                npm run build

      - put: app-image
        params:
          build: source-code
          build_args:
            NODE_ENV: production
```

To deploy and trigger the pipeline:

```bash
# Login to Concourse
fly -t main login -c http://ci.example.com:8080

# Set (create or update) the pipeline
fly -t main set-pipeline -p myapp -c pipeline.yml

# Unpause to enable automatic triggers
fly -t main unpause-pipeline -p myapp
```

### Strengths and Weaknesses

**Strengths:**
- Pure pipeline-as-code — no UI-based job configuration, everything is versioned YAML
- Full build reproducibility through resource versioning
- Clean separation of resource fetching, task execution, and output production
- Excellent for GitOps workflows — pipeline definitions live in Git alongside application code
- `fly` CLI enables programmatic pipeline management and CI/CD of your CI/CD
- Built-in support for time-triggered jobs, manual gates, and serial job execution
- Immutable build containers — no shared state between runs
- Strong multi-tenancy with team-based isolation

**Weaknesses:**
- Steep learning curve — resource and job concepts are abstract and take time to master
- No native Docker-in-Docker support — building images requires workarounds
- Smaller community means fewer tutorials and third-party resources
- Web UI is minimalistic and lacks advanced build visualization
- PostgreSQL dependency adds operational complexity compared to SQLite-based alternatives
- Resource types must be pre-registered or loaded as custom types
- Less suitable for simple projects — the abstraction overhead is significant

## Feature Comparison

| Feature | Woodpecker CI | Drone | Jenkins | Concourse CI |
|---------|:---:|:---:|:---:|:---:|
| **Pipeline Syntax** | YAML | YAML | Groovy DSL | YAML + fly CLI |
| **Container-Native** | Yes | Yes | Via plugins | Yes (Garden) |
| **Setup Complexity** | Low | Low | High | Medium |
| **Plugin Ecosystem** | Small | Medium | Massive (1800+) | Small |
| **Kubernetes Support** | Native agent | Via runner | Via plugin | Native |
| **Matrix Builds** | Yes | Limited | Yes | Via plan config |
| **Secret Management** | Built-in + external | Built-in + Vault | Credentials plugin | Credential manager |
| **Multi-Tenancy** | Teams/Orgs | Teams/Orgs | Folders + RBAC | Teams |
| **Resource Usage** | ~50 MB/server | ~50 MB/server | ~4 GB+ controller | ~500 MB+ ATC |
| **Artifact Storage** | External (S3) | External (S3) | Built-in + plugins | External only |
| **Build Caching** | Workspace volumes | Workspace volumes | Workspace + plugins | Resource caching |
| **Web UI Quality** | Modern, clean | Functional | Blue Ocean available | Minimalist |
| **Active Development** | Very active | Moderate | Very active | Moderate |
| **Learning Curve** | Low | Low | High | High |
| **License** | Apache 2.0 | Apache 2.0 | MIT | Apache 2.0 |

## Which Platform Should You Choose?

### Choose Woodpecker CI if:
- You want the simplest setup with modern defaults
- You use Gitea or Forgejo (first-class integration)
- You prefer active open-source community development
- Your team values clean YAML syntax over complex DSLs
- You need Kubernetes-native execution for steps

### Choose Drone if:
- You want a proven, stable platform with enterprise backing
- You need a rich plugin marketplace out of the box
- Your team is already familiar with Drone from previous roles
- You require signed RPC communication between server and runners
- You need multi-runner type support (Docker, Kubernetes, Exec)

### Choose Jenkins if:
- You have complex, multi-language build requirements
- You need the largest possible plugin ecosystem
- Your team has existing Jenkins expertise
- You require Windows or macOS build agents alongside Linux
- You need Shared Libraries for cross-repository pipeline reuse
- Backwards compatibility with legacy build systems is critical

### Choose Concourse CI if:
- You practice GitOps and want everything version-controlled
- Build reproducibility is a hard requirement
- You value immutability and clean resource abstractions
- Your team is comfortable with YAML + CLI workflows
- You are already in the VMware/Tanzu ecosystem
- You need strong multi-tenant isolation between teams

## Production Deployment Recommendations

Regardless of which platform you choose, follow these production best practices:

**1. Use HTTPS everywhere.** Place a reverse proxy (Nginx, Traefik, or Caddy) in front of your CI/CD server with TLS termination:

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

    # WebSocket support for live build logs
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**2. Separate build workloads from the controller.** Never run build steps on the same machine as your CI/CD server. Use dedicated agent/worker nodes — this prevents a rogue build from compromising your server and enables horizontal scaling.

**3. Automate agent provisioning.** Use cloud-init scripts or Terraform to spin up CI/CD agents on demand. For Kubernetes-based platforms, configure Horizontal Pod Autoscaler rules based on pending build queue depth.

**4. Back up pipeline definitions.** Store all pipeline YAML or Groovy files in Git alongside your application code. Treat your CI/CD configuration as application code — review, test, and version it.

**5. Implement resource limits.** Docker and Kubernetes both support CPU and memory limits per build container. Without limits, a single misconfigured build can exhaust your worker node's resources and block all other pipelines:

```yaml
# Docker resource constraints for build agents
# Add to your docker-compose or docker run command
docker run --cpus=4 --memory=8g --memory-swap=8g ...
```

**6. Rotate secrets regularly.** Use your platform's built-in secret rotation or integrate with HashiCorp Vault. Never store plaintext secrets in pipeline files. Most platforms support secret references like `from_secret` or `((credential-name))` that resolve at runtime.

**7. Monitor build performance.** Track metrics like average build duration, queue wait time, and failure rate. Set up alerts when builds exceed expected durations or failure rates spike — these are early indicators of infrastructure problems.

## Conclusion

The self-hosted CI/CD landscape in 2026 offers mature options for every scenario. **Woodpecker CI** leads in simplicity and community momentum, making it the best choice for new deployments. **Drone** provides enterprise stability with a rich plugin ecosystem. **Jenkins** remains unmatched for complex, heterogeneous build environments despite its operational overhead. **Concourse CI** excels for teams practicing GitOps who prioritize reproducibility and immutability above all else.

For most teams starting a new self-hosted CI/CD deployment in 2026, Woodpecker CI offers the best balance of features, simplicity, and active development. Its clean YAML syntax, low resource footprint, and strong Gitea/Forgejo integration make it the natural choice for organizations that value developer experience alongside infrastructure control.

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
