---
title: "Self-Hosted DevOps Dashboard — Hygieia, Build Radiator & CI Status Board Comparison"
date: 2026-05-02
draft: false
tags:
  - devops
  - monitoring
  - ci-cd
  - dashboard
  - self-hosted
---

When your CI/CD pipeline spans multiple tools — Jenkins, GitLab CI, GitHub Actions, SonarQube, Nexus, Jira — keeping track of build health, deployment status, and code quality becomes a full-time job. Self-hosted DevOps dashboards aggregate all these signals into a single pane of glass, letting your team see the entire delivery pipeline at a glance.

In this guide, we compare three open-source approaches to DevOps visibility: **Hygieia** (Capital One's enterprise dashboard platform), **Build Monitor / CI Radiator** solutions for team display boards, and **custom CI status dashboards** built from pipeline APIs.

## Why You Need a DevOps Dashboard

Without a centralized dashboard, DevOps teams waste time switching between Jenkins, GitLab, SonarQube, artifact registries, and ticket trackers to answer simple questions:

- Is the latest build green?
- Which services have failed code quality gates?
- When was the last production deployment?
- Are there outstanding security vulnerabilities?

A self-hosted DevOps dashboard pulls metrics from all these systems via APIs and presents them on a single screen — ideal for team TV displays, standup meetings, and operations centers.

## Comparison Table

| Feature | Hygieia | CI Build Radiator | Custom API Dashboard |
|---------|---------|-------------------|---------------------|
| **GitHub Stars** | 3,800+ | 500–1,500 | N/A |
| **CI Integrations** | Jenkins, GitLab, GitHub Actions, Bamboo | Jenkins, Travis, CircleCI | Any (via REST API) |
| **Code Quality** | SonarQube, Fortify, Checkmarx | Limited | Custom |
| **Deployment Tracking** | Yes (UDeploy, Jenkins) | No | Custom |
| **Security Scanning** | Nexus IQ, WhiteSource, Snyk | No | Custom |
| **Docker Support** | Yes (docker-compose) | Yes | Yes |
| **Database** | MongoDB | N/A (stateless) | Your choice |
| **Setup Complexity** | High | Low | Medium |
| **Best For** | Enterprise teams | Team display boards | Custom workflows |

## Hygieia — Enterprise DevOps Dashboard

Hygieia, originally developed by Capital One and donated to the CD Foundation, is the most comprehensive open-source DevOps dashboard available. It collects data from your entire software delivery pipeline — source control, CI, code quality, security scanning, artifact management, and deployment — and presents it through a customizable widget-based UI.

### Architecture

Hygieia uses a collector-based architecture. Each collector connects to a specific tool (Jenkins, GitHub, SonarQube, etc.) and pushes normalized data to a MongoDB backend. The API server exposes this data to the Angular-based UI.

### Key Features

- **Multi-CI support**: Jenkins, Hudson, GitLab CI, GitHub Actions
- **Code quality integration**: SonarQube, Fortify, Checkmarx
- **Security scanning**: Nexus IQ, WhiteSource, Snyk, Dependency-Check
- **Artifact tracking**: Nexus, Artifactory
- **Deployment tracking**: uDeploy, Jenkins deployment jobs
- **Custom widgets**: Build your own dashboard views

### Docker Compose Deployment

```yaml
version: '3'
services:
  mongodb:
    image: mongo:4.4
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db
    command: mongod --noauth

  api:
    image: hygieia/hygieia-api:latest
    ports:
      - "8080:8080"
    environment:
      - SPRING_DATA_MONGODB_HOST=mongodb
      - SPRING_DATA_MONGODB_PORT=27017
      - SPRING_DATA_MONGODB_DATABASE=dashboarddb
      - SPRING_DATA_MONGODB_USERNAME=dashboarduser
      - SPRING_DATA_MONGODB_PASSWORD=dbpassword
    depends_on:
      - mongodb

  jenkins-collector:
    image: hygieia/jenkins-build-collector:latest
    environment:
      - SPRING_DATA_MONGODB_HOST=mongodb
      - JENKINS_CRON=0 * * * * *
      - JENKINS_SERVERS=[{"url":"http://jenkins:8080","user":"admin","apiKey":"token"}]
    depends_on:
      - mongodb

  ui:
    image: hygieia/hygieia-ui:latest
    ports:
      - "3000:3000"
    depends_on:
      - api

volumes:
  mongodb_data:
```

### GitHub Stats

| Metric | Value |
|--------|-------|
| Stars | 3,835 |
| Last Updated | September 2023 |
| Description | Capital One's DevOps Dashboard platform |

**Note**: While Hygieia's development has slowed, the core platform remains functional for teams already invested in its ecosystem. For new deployments, consider lighter-weight alternatives below.

## CI Build Radiator — Team Display Boards

A CI build radiator (also called a build monitor or information radiator) is a focused dashboard designed for large-screen display in team areas. Unlike Hygieia's enterprise scope, a build radiator focuses on one thing: showing the current state of all builds.

### Popular Options

| Tool | Description | Docker | Stars |
|------|-------------|--------|-------|
| **Build Monitor View** | Jenkins plugin with dedicated full-screen view | N/A (plugin) | 300+ |
| **Nevergreen** | Build radiator with multi-CI support | Yes | Growing |
| **CI Eye** | Minimalist build status display | Yes | 200+ |
| **BuildReactor** | Chrome extension + dashboard | Browser ext | 150+ |

### Simple Build Radiator with Docker

For teams that need a quick, lightweight solution, you can build a build radiator using a simple web dashboard that polls CI APIs:

```yaml
version: '3'
services:
  build-radiator:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./radiator.html:/usr/share/nginx/html/index.html:ro
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    restart: unless-stopped
```

The HTML dashboard fetches build statuses via JavaScript:

```javascript
// Poll Jenkins API every 30 seconds
async function fetchJenkinsBuilds() {
  const response = await fetch('/api/jenkins/job/my-project/api/json');
  const data = await response.json();
  
  data.jobs.forEach(job => {
    const status = job.color === 'blue' ? 'success' : 'failure';
    updateBuildCard(job.name, status, job.lastBuildTimestamp);
  });
}

setInterval(fetchJenkinsBuilds, 30000);
```

## Custom CI Status Dashboard — API-Driven Approach

When off-the-shdashboards don't fit your workflow, building a custom dashboard from CI/CD APIs gives you complete control. This approach works well when you need to combine data from sources that no single dashboard supports.

### Data Sources

Most CI/CD tools expose REST APIs that return build status, duration, and metadata:

```bash
# Jenkins API
curl -s http://jenkins:8080/api/json?tree=jobs[name,color,lastBuild[timestamp,result]]

# GitLab CI API
curl -s --header "PRIVATE-TOKEN: $TOKEN" \
  "https://gitlab.example.com/api/v4/projects?simple=true"

# GitHub Actions API
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/org/repo/actions/runs?per_page=5"
```

### Example: Unified Status Dashboard

```python
#!/usr/bin/env python3
"""Aggregate CI/CD statuses from multiple sources."""
import json
from datetime import datetime

sources = {
    "jenkins": {"url": "http://jenkins:8080/api/json", "type": "jenkins"},
    "gitlab": {"url": "https://gitlab/api/v4/projects", "type": "gitlab"},
    "github": {"url": "https://api.github.com/repos/org/repo/actions/runs", "type": "github"},
}

def get_build_status(source_name, config):
    """Fetch and normalize build status from a CI source."""
    # Implementation depends on source API
    pass

def render_dashboard(statuses):
    """Generate HTML dashboard from aggregated statuses."""
    html = "<html><head><title>CI Status</title></head><body>"
    html += "<h1>Build Status Dashboard</h1>"
    html += "<table><tr><th>Project</th><th>Status</th><th>Duration</th></tr>"
    for name, status in statuses.items():
        color = "green" if status["success"] else "red"
        html += f"<tr><td>{name}</td><td style='color:{color}'>{status['state']}</td></tr>"
    html += "</table></body></html>"
    return html
```

## When to Choose Each Approach

| Scenario | Recommended |
|----------|-------------|
| Enterprise with 10+ tools in the pipeline | Hygieia |
| Team needs a TV display for build status | Build Radiator |
| Custom metrics or unusual tool combinations | Custom API Dashboard |
| Small team with single CI tool | CI tool's built-in dashboard |
| Compliance/audit reporting needs | Hygieia (historical data) |

## For Related Reading

If you're building a complete DevOps toolchain, check our other guides:

- [CI/CD Pipeline Comparison](../2026-04-19-woodpecker-ci-vs-drone-ci-vs-gitea-actions-self-hosted-cicd-guide-2026/) — Woodpecker vs Drone vs Gitea Actions
- [Build Cache Solutions](../2026-04-23-sccache-vs-ccache-vs-icecream-self-hosted-build-cache-2026/) — sccache vs ccache vs Icecc
- [CI/CD Platforms](../2026-04-26-screwdriver-ci-vs-agola-vs-prow-self-hosted-cicd-platforms-2026/) — Screwdriver vs Agola vs Prow

## FAQ

### What is a DevOps dashboard?

A DevOps dashboard is a centralized visualization tool that aggregates metrics from your entire software delivery pipeline — including source control, continuous integration, code quality analysis, security scanning, artifact management, and deployment systems. It provides a single pane of glass for monitoring the health and performance of your delivery pipeline.

### Is Hygieia still actively maintained?

Hygieia's primary development slowed after 2023, with the last significant commit in September 2023. However, the platform remains functional and is still used by organizations that deployed it during its active development phase. For new deployments, consider lighter alternatives like CI build radiators or custom API dashboards.

### What's the difference between a DevOps dashboard and a build radiator?

A DevOps dashboard (like Hygieia) provides comprehensive pipeline visibility across multiple tools and stages — CI, code quality, security, artifacts, and deployments. A build radiator is focused narrowly on showing the current build status of CI jobs, typically designed for large-screen display in team areas. Build radiators are simpler to set up but offer less depth.

### Can I use Hygieia with GitHub Actions?

Hygieia has a GitHub collector that can fetch repository data, but GitHub Actions-specific collection is limited. The GitHub collector primarily tracks commits, pull requests, and repository metadata. For detailed GitHub Actions build data, you may need to write a custom collector or use the custom API dashboard approach.

### How do I set up a build radiator for my team?

The simplest approach is to use your CI tool's built-in dashboard view. For Jenkins, install the Build Monitor View plugin. For multi-CI environments, deploy a build radiator container that polls multiple CI APIs and displays results on a large screen. Most solutions require 5–15 minutes to configure.

### What database does Hygieia require?

Hygieia requires MongoDB as its backend database. All collector data is normalized and stored in MongoDB, which the API server then queries to serve the UI. You can run MongoDB via Docker as shown in the docker-compose example above.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DevOps Dashboard — Hygieia, Build Radiator & CI Status Board Comparison",
  "description": "Compare self-hosted DevOps dashboard solutions including Hygieia, CI build radiators, and custom API dashboards. Find the right pipeline visibility tool for your team.",
  "datePublished": "2026-05-02",
  "dateModified": "2026-05-02",
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
