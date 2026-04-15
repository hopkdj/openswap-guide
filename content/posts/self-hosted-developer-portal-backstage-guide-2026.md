---
title: "Complete Guide to Self-Hosted Developer Portals: Backstage and Beyond 2026"
date: 2026-04-15
tags: ["developer-portal", "backstage", "internal-developer-platform", "self-hosted", "devops"]
draft: false
description: "Build your own internal developer platform with open-source tools. Complete guide to Backstage, self-hosted developer portals, service catalogs, and scaffolder templates for 2026."
---

Every growing engineering team eventually hits the same wall: too many services, too many repositories, scattered documentation, inconsistent tooling, and onboarding new developers takes weeks instead of days. A **developer portal** solves this by providing a single pane of glass for all your internal services, APIs, documentation, and tooling.

While companies like Spotify (who created Backstage), Netflix, and Stripe have invested millions in their internal developer platforms, you don't need a massive budget to build one. Open-source and self-hosted options let any team create a professional developer portal on their own infrastructure.

## Why You Need a Self-Hosted Developer Portal

Internal developer portals are becoming essential infrastructure for teams with more than a handful of microservices. Here's why building one on your own servers makes sense:

### The Problem of Developer Friction

When developers spend hours searching for the right repository, guessing which API endpoint to call, or asking teammates "how do I deploy this?" — that's friction that directly reduces engineering velocity. A developer portal eliminates this by centralizing:

- **Service catalog** — every microservice, library, and application in one searchable index
- **API documentation** — auto-generated from OpenAPI specs, linked to the owning team
- **Scaffolder templates** — new project boilerplate generated in minutes, not hours
- **Ownership tracking** — clear mapping of who maintains what, with escalation paths
- **Scorecards and standards** — automated checks for documentation, tests, and security compliance

### Self-Hosted vs. SaaS Developer Portals

Cloud-based developer portal services like Port, Compass (Atlassian), and Cortex offer convenience but come with trade-offs:

| Feature | Self-Hosted (Backstage) | SaaS (Port, Cortex) |
|---------|------------------------|---------------------|
| **Data privacy** | Full control, never leaves your infra | Data stored on vendor servers |
| **Customization** | Unlimited — open-source codebase | Limited to vendor-provided features |
| **Cost at scale** | Infrastructure cost only (~$50-200/mo) | Per-seat pricing ($50-150/user/mo) |
| **Vendor lock-in** | None — you own everything | High — migration is painful |
| **Setup complexity** | Higher — requires DevOps effort | Lower — managed service |
| **Plugin ecosystem** | 800+ community plugins | Limited integrations |
| **SLA control** | You define it | Dependent on vendor uptime |
| **Integration with internal tools** | Direct database/API access | Requires webhooks or API sync |

For teams that value data sovereignty, have complex internal tooling, or want to avoid per-seat licensing at scale, self-hosted is the clear winner.

## Backstage: The Gold Standard for Open-Source Developer Portals

[Backstage](https://backstage.io/) is an open-source developer portal framework originally built by Spotify and now a CNCF incubating project. It provides the core building blocks — service catalog, software templates, tech docs, and a plugin system — that you extend to match your organization's needs.

### Core Architecture

Backstage consists of three main components:

1. **Software Catalog** — entity registry that tracks services, components, APIs, resources, and systems. Entities are defined as YAML files in your repositories and ingested via the catalog processor.

2. **Software Templates (Scaffolder)** — parameterized templates that bootstrap new projects with your organization's standards, CI/CD pipelines, and infrastructure-as-code configurations.

3. **TechDocs** — documentation-as-code system that renders Markdown documentation from repositories directly in the portal, supporting a "docs like code" workflow.

### Installing Backstage with Docker Compose

The fastest way to get Backstage running is with Docker Compose. Here's a production-ready setup:

```yaml
version: '3.8'

services:
  backstage:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "7007:7007"
    environment:
      - NODE_ENV=production
      - POSTGRES_HOST=postgres
      - POSTGRES_PORT=5432
      - POSTGRES_USER=backstage
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=backstage
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - backstage-net

  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=backstage
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=backstage
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U backstage"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - backstage-net

volumes:
  pgdata:

networks:
  backstage-net:
    driver: bridge
```

Save this as `docker-compose.yml` and create your `.env`:

```bash
POSTGRES_PASSWORD=your-secure-password-here
```

### Building the Backstage App

Backstage requires a Node.js application as its frontend and backend. Create it using the official CLI:

```bash
# Install the Backstage CLI
npx @backstage/create-app@latest

# This creates an app with:
# - packages/app (frontend React application)
# - packages/backend (Node.js backend server)
# - app-config.yaml (configuration)

# Install dependencies
cd my-backstage-app
yarn install

# Build for production
yarn build:backend
```

Create a Dockerfile for the backend:

```dockerfile
FROM node:20-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    git dumb-init tini && rm -rf /var/lib/apt/lists/*
RUN yarn config set network-timeout 300000
WORKDIR /app
COPY yarn.lock package.json packages/backend/dist/skeleton.tar.gz ./
RUN tar xzf skeleton.tar.gz && rm skeleton.tar.gz
RUN yarn install --production --frozen-lockfile
COPY packages/backend/dist/bundle.tar.gz .
RUN tar xzf bundle.tar.gz && rm bundle.tar.gz
CMD ["dumb-init", "node", "packages/backend", "--config", "app-config.yaml"]
```

Build and run:

```bash
docker compose up -d --build
```

Access the portal at `http://localhost:7007`.

### Configuring the Software Catalog

The catalog is the heart of Backstage. Define entities using YAML files. Here's a comprehensive example:

```yaml
# catalog-info.yaml (place in each repository root)
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: payment-service
  description: Handles payment processing and refunds
  annotations:
    github.com/project-slug: myorg/payment-service
    backstage.io/techdocs-ref: dir:.
    sonarqube.org/project-key: myorg_payment-service
    prometheus.io/alert: myorg-payment-service
    grafana.com/dashboard-selector: >-
      labels.app_kubernetes_io_name == "payment-service"
  tags:
    - java
    - spring-boot
    - production
    - pci-dss
  links:
    - url: https://grafana.internal/d/payment-service
      title: Grafana Dashboard
      icon: dashboard
    - url: https://logs.internal/payment-service
      title: Log Dashboard
      icon: bugReport
spec:
  type: service
  lifecycle: production
  owner: payments-team
  system: payment-platform
  dependsOn:
    - resource:default/postgres-payments
    - component:default/fraud-detection-service
```

For group and user entities (team ownership):

```yaml
# group.yaml
apiVersion: backstage.io/v1alpha1
kind: Group
metadata:
  name: payments-team
  description: Team responsible for payment processing
spec:
  type: team
  profile:
    displayName: Payments Team
    email: payments@myorg.com
    slack: '#payments-team'
  parent: engineering
  children: []
  members: [alice, bob, charlie]
```

### Setting Up the Catalog Processor

To automatically ingest catalog info from all your repositories, configure the catalog processor:

```yaml
# app-config.yaml
catalog:
  import:
    entityFilename: catalog-info.yaml
    pullRequestBranchName: backstage-integration
  rules:
    - allow: [Component, API, Resource, System, Group, User, Domain, Location]
  locations:
    # Discover all catalog files across your GitHub org
    - type: github-discovery
      target: https://github.com/myorg/*/blob/main/catalog-info.yaml
      rules:
        - allow: [Component, API, Resource, System]

    # Static location for shared resources
    - type: file
      target: ../../catalog/shared-resources.yaml
      rules:
        - allow: [Resource]

    # TechDocs documentation locations
    - type: github-discovery
      target: https://github.com/myorg/*/blob/main/mkdocs.yml
      rules:
        - allow: [Component]

providers:
  github:
    providerId:
      organization: 'myorg'
      catalogPath: '/catalog-info.yaml'
      filters:
        repository: '.*'
      schedule:
        frequency: { hours: 1 }
        timeout: { minutes: 3 }
```

### Software Templates (Scaffolder)

Templates are what make Backstage genuinely powerful — they let developers bootstrap new services in minutes with all your organization's standards baked in.

```yaml
# templates/spring-boot-service/template.yaml
apiVersion: scaffolder.backstage.io/v1beta3
kind: Template
metadata:
  name: spring-boot-service
  title: Spring Boot Microservice
  description: Create a new Spring Boot microservice with CI/CD, monitoring, and security best practices
  tags:
    - java
    - spring-boot
    - microservice
spec:
  owner: platform-engineering
  type: service

  parameters:
    - title: Service Information
      required:
        - serviceName
        - description
        - owner
      properties:
        serviceName:
          title: Service Name
          type: string
          pattern: '^[a-z][a-z0-9-]+$'
          description: Kebab-case name for the service
          ui:autofocus: true
        description:
          title: Description
          type: string
          description: What this service does
        owner:
          title: Team Owner
          type: string
          ui:field: OwnerPicker
          ui:options:
            catalogFilter:
              kind: Group

    - title: Configuration
      required:
        - database
      properties:
        database:
          title: Database Type
          type: string
          enum:
            - postgresql
            - mysql
            - none
          default: postgresql
        includeRedis:
          title: Include Redis Cache
          type: boolean
          default: false
        includeKafka:
          title: Include Kafka Integration
          type: boolean
          default: false

  steps:
    - id: fetch-base
      name: Fetch Base Template
      action: fetch:template
      input:
        url: ./skeleton
        targetPath: ./service
        values:
          serviceName: ${{ parameters.serviceName }}
          description: ${{ parameters.description }}
          owner: ${{ parameters.owner }}
          database: ${{ parameters.database }}
          includeRedis: ${{ parameters.includeRedis }}
          includeKafka: ${{ parameters.includeKafka }}
          orgName: myorg

    - id: publish
      name: Publish to GitHub
      action: publish:github
      input:
        allowedHosts: ['github.com']
        description: ${{ parameters.description }}
        repoUrl: github.com?owner=myorg&repo=${{ parameters.serviceName }}
        defaultBranch: main
        protectDefaultBranch: true
        allowAutoMerge: true

    - id: register
      name: Register to Catalog
      action: catalog:register
      input:
        repoContentsUrl: ${{ steps.publish.output.repoContentsUrl }}
        catalogInfoPath: '/catalog-info.yaml'

  output:
    links:
      - title: Repository
        url: ${{ steps.publish.output.remoteUrl }}
      - title: Open in Backstage
        icon: catalog
        entityRef: ${{ steps.register.output.entityRef }}
```

The template skeleton (`./skeleton/`) contains your actual project files with EJS templating:

```yaml
# skeleton/catalog-info.yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: ${{ values.serviceName }}
  description: ${{ values.description }}
  annotations:
    github.com/project-slug: myorg/${{ values.serviceName }}
    backstage.io/techdocs-ref: dir:.
  tags:
    - java
    - spring-boot
spec:
  type: service
  lifecycle: experimental
  owner: ${{ values.owner }}
```

```yaml
# skeleton/.github/workflows/ci.yml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    services:
      {% if values.database == 'postgresql' %}
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
      {% endif %}
      {% if values.includeRedis %}
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
      {% endif %}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '21'
      - run: ./mvnw verify
```

### TechDocs: Documentation as Code

Backstage's TechDocs renders documentation directly from repositories. Configure it with:

```yaml
# app-config.yaml (TechDocs section)
techdocs:
  builder: 'local'
  generator:
    runIn: 'local'
    input:
      install:
        - python3 -m pip install mkdocs-techdocs-core==1.*
  publisher:
    type: 'local'
    workingDirectory: '/tmp/techdocs'
```

Then in each service repository, create a `mkdocs.yml`:

```yaml
# mkdocs.yml
site_name: Payment Service
nav:
  - Home: index.md
  - Architecture: architecture.md
  - API Reference: api.md
  - Runbook: runbook.md
  - On-Call: oncall.md

plugins:
  - techdocs-core
```

Documentation lives alongside code and renders beautifully in the portal with search and navigation.

## Essential Plugins for Production Backstage

The real power of Backstage comes from its plugin ecosystem. Here are the most valuable ones:

| Plugin | Purpose | Category |
|--------|---------|----------|
| `@backstage/plugin-kubernetes` | Kubernetes resource visualization | Infrastructure |
| `@backstage/plugin-sonarqube` | Code quality metrics | Quality |
| `@backstage/plugin-jenkins` | CI/CD pipeline status | CI/CD |
| `@backstage/plugin-sentry` | Error tracking integration | Monitoring |
| `@backstage/plugin-prometheus` | Metrics and alerting | Monitoring |
| `@backstage/plugin-tech-radar` | Technology radar visualization | Governance |
| `@backstage/plugin-scorecard` | Service maturity scoring | Governance |
| `@backstage/plugin-cost-insights` | Cloud cost tracking | FinOps |
| `@backstage/plugin-graphiql` | GraphQL API explorer | Development |
| `@backstage/plugin-lighthouse` | Web performance audits | Quality |

Install plugins in your backend:

```bash
# From your Backstage app directory
cd packages/backend
yarn add @backstage/plugin-kubernetes-backend @backstage/plugin-sonarqube-backend

cd packages/app
yarn add @backstage/plugin-kubernetes @backstage/plugin-sonarqube
```

## Running Backstage in Production

### Nginx Reverse Proxy with TLS

```nginx
server {
    listen 80;
    server_name portal.myorg.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name portal.myorg.com;

    ssl_certificate /etc/letsencrypt/live/portal.myorg.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/portal.myorg.com/privkey.pem;

    location / {
        proxy_pass http://localhost:7007;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Enable gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;
}
```

### Authentication Setup

Backstage supports multiple authentication providers. For a self-hosted setup with Keycloak:

```yaml
# app-config.yaml
auth:
  environment: production
  providers:
    oidc:
      production:
        clientId: ${AUTH_OIDC_CLIENT_ID}
        clientSecret: ${AUTH_OIDC_CLIENT_SECRET}
        metadataUrl: ${AUTH_OIDC_METADATA_URL}
        prompt: auto
        scope: openid profile email

catalog:
  providers:
    oidc:
      production:
        factory: 'oidc'
        defaultNamespace: default
```

### Scaling for Large Organizations

For organizations with thousands of services:

```yaml
# app-config.yaml - Performance tuning
catalog:
  providers:
    github:
      providerId:
        schedule:
          frequency: { hours: 2 }
          timeout: { minutes: 10 }
          initialDelay: { seconds: 30 }
        entityRefreshDuration: { minutes: 30 }

backend:
  database:
    client: pg
    connection:
      host: ${POSTGRES_HOST}
      port: ${POSTGRES_PORT}
      user: ${POSTGRES_USER}
      password: ${POSTGRES_PASSWORD}
      database: ${POSTGRES_DB}
      pool:
        min: 2
        max: 10
        idleTimeoutMillis: 30000
```

## Best Practices for Developer Portal Success

### Start Small, Iterate Fast

Don't try to catalog every service on day one. Start with:

1. **Core services** — your top 10-20 most important services
2. **One template** — the most common project type your team creates
3. **Basic docs** — README files for each service, nothing fancy

Expand gradually as adoption grows.

### Make Catalog Updates Automatic

The biggest failure mode for developer portals is stale data. Solve this with:

- **CI/CD integration** — validate `catalog-info.yaml` in every PR
- **Automated discovery** — scan repos daily for new services
- **Slack reminders** — notify owners when catalog info hasn't been updated in 90 days

```yaml
# GitHub Action to validate catalog-info.yaml
name: Validate Catalog
on:
  push:
    paths:
      - 'catalog-info.yaml'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: RoadieHQ/backstage-catalog-validator@v1
        with:
          path: './catalog-info.yaml'
```

### Use Scorecards to Drive Standards

Backstage scorecards let you define and track standards:

```yaml
# scorecard.yaml
apiVersion: backstage.io/v1alpha1
kind: Scorecard
metadata:
  name: production-ready
  description: Criteria for production deployment
spec:
  targets:
    - kind: Component
      filter: "spec.lifecycle = 'production'"
  checks:
    - name: Has README
      description: Service has documented README
      weight: 2
    - name: Has Owner
      description: Service has an assigned owner
      weight: 3
    - name: CI Pipeline
      description: CI pipeline passes on main branch
      weight: 3
    - name: Monitoring Configured
      description: Prometheus alerts are configured
      weight: 2
    - name: Security Scan
      description: No critical CVEs in dependencies
      weight: 5
```

### Measure Portal Adoption

Track metrics that matter:

- **Time to onboard** new developers (target: under 1 day)
- **Time to create** a new service (target: under 15 minutes with templates)
- **Catalog coverage** — percentage of services registered (target: over 95%)
- **Template usage** — how many services were scaffolded vs. created manually
- **Portal DAU** — daily active users of the developer portal

## Alternative Self-Hosted Options

While Backstage dominates the open-source space, there are other approaches worth considering:

### Lightweight Alternatives

If Backstage feels too heavy for your team, consider:

| Solution | Best For | Complexity |
|----------|----------|------------|
| **Backstage** | Full-featured developer portal | High |
| **Static HTML + Hugo** | Small teams, simple catalog | Low |
| **GitLab Internal Portal** | GitLab-heavy shops | Medium |
| **Custom dashboard** | Unique requirements | Variable |

For teams under 20 engineers, a well-organized `README.md` in a central `docs/` repository with a static site generator can serve as a lightweight developer portal. The key is having a single source of truth — the tool matters less than the discipline.

### Enterprise Platforms with Self-Hosted Options

- **Mia-Platform Developer Portal** — enterprise-focused, Kubernetes-native
- **Humanitec** — internal developer platform with self-hosted option
- **Custom-built with React + GraphQL** — for teams with unique requirements

## Conclusion

A self-hosted developer portal built on Backstage gives your team the same capabilities that top tech companies spend millions developing internally. The investment in setup pays back quickly through faster onboarding, standardized tooling, and reduced developer friction.

Start with the catalog, add one template, and iterate based on feedback. The open-source community around Backstage is massive and growing — with over 800 plugins and contributions from companies like Spotify, Netflix, Airbnb, and American Airlines. Your team doesn't have to build this from scratch; you're standing on the shoulders of giants.

The best developer portal is the one your team actually uses. Keep it simple, make it fast, and let the content come from the code repositories themselves. With Backstage running on your own infrastructure, you control the data, the features, and the roadmap.
