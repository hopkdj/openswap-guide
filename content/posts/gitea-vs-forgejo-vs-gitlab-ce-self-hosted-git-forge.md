---
title: "Gitea vs Forgejo vs GitLab CE: Best Self-Hosted Git Forge 2026"
date: 2026-04-12
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete comparison of self-hosted Git forges in 2026: Gitea, Forgejo, and GitLab Community Edition. Docker setup, feature breakdown, and migration guide."
---

When you want full control over your source code, nothing beats running your own Git forge. The big three in the self-hosted space — **Gitea**, **Forgejo**, and **GitLab CE** — each take a different approach to the same problem. This guide breaks down their differences, shows you how to deploy each one, and helps you pick the right fit for your team.

## Why Self-Host Your Git Forge

Running your own code hosting platform gives you advantages that no SaaS can match:

- **Complete data sovereignty** — your code, your issues, your CI pipelines never leave your infrastructure. No surprise ToS changes, no forced migrations.
- **Unlimited private repositories** — no per-seat pricing for private repos, no feature gating behind enterprise tiers.
- **Custom CI/CD pipelines** — runners execute on hardware you control, with access to internal networks, registries, and secrets.
- **Zero vendor lock-in** — migrate between instances, back up on your schedule, and integrate with any tool in your stack.
- **Compliance and auditing** — full control over access logs, retention policies, and data residency requirements.

Whether you are a solo developer tired of GitHub rate limits, a small team that needs internal code review workflows, or an organization with strict data governance requirements, a self-hosted Git forge pays for itself quickly.

## The Three Contenders

### Gitea — Lightweight and Fast

Gitea started as a community fork of Gogs and has grown into the most popular lightweight Git forge. Written in Go, it compiles to a single binary, runs on a Raspberry Pi, and starts in under a second. It mirrors GitHub's UI closely, making the transition effortless for most developers.

As of 2026, Gitea is maintained by a commercial entity (Gitea Ltd) after a controversial reorganization in late 2024 that transferred the repository and trademark. This sparked the creation of Forgejo.

### Forgejo — The Community Fork

Forgejo ("for-jay-oh") forked from Gitea in December 2024 as a response to governance concerns. It is a **hard fork** — meaning the codebases share a common ancestor but are developing independently. Forgejo is governed by the **Forgejo Community**, a non-profit structure designed to prevent any single entity from controlling the project.

Key differentiators:
- **Fediverse integration** (ActivityPub) — your forge can interact with Mastodon, PeerTube, and other federated platforms
- **Strict open-source commitment** — no telemetry, no proprietary features
- **Community governance** — decisions made through open voting, not corporate leadership
- **Forgejo Actions** — built-in CI/CD compatible with GitHub Actions workflows

Forgejo tracks Gitea releases closely but adds its own features and patches. The project has gained significant traction among privacy-focused organizations and open-source purists.

### GitLab Community Edition — The Full-Featured Behemoth

GitLab CE is the open-source edition of GitLab. It is far more than a Git forge — it is a complete DevOps platform with built-in CI/CD, container registry, package registry, security scanning, and more.

The tradeoff is resource consumption: GitLab recommends **4 CPU cores and 8 GB RAM minimum**, while Gitea and Forgejo run comfortably on 512 MB RAM. GitLab CE is the right choice when you need an all-in-one DevOps platform and have the infrastructure to support it.

## Feature Comparison

| Feature | Gitea 1.23+ | Forgejo 10+ | GitLab CE 17+ |
|---------|-------------|-------------|----------------|
| **Language** | Go | Go | Ruby + Go |
| **Minimum RAM** | 256 MB | 256 MB | 8 GB |
| **Database** | SQLite, MySQL, PostgreSQL, MSSQL | SQLite, MySQL, PostgreSQL, MSSQL | PostgreSQL only |
| **Built-in CI/CD** | Gitea Actions (Actions-compatible) | Forgejo Actions (Actions-compatible) | GitLab CI (YAML-based) |
| **Package Registry** | Yes | Yes | Yes (comprehensive) |
| **Container Registry** | Yes | Yes | Yes |
| **Wiki** | Yes | Yes | Yes |
| **Issue Tracking** | Yes | Yes | Yes (advanced) |
| **Federation (ActivityPub)** | No | Yes | No |
| **Kanban Boards** | Yes | Yes | Yes |
| **Merge/Pull Requests** | Yes | Yes | Yes (Merge Requests) |
| **Code Owners** | Yes | Yes | Yes |
| **Security Scanning** | Limited | Limited | Comprehensive (SAST, DAST, dependency) |
| **Container Scanning** | No | No | Yes |
| **LFS Support** | Yes | Yes | Yes |
| **Webhooks** | Yes | Yes | Yes |
| **OAuth2 / SSO** | Yes | Yes | Yes (extensive providers) |
| **Two-Factor Auth** | Yes | Yes | Yes |
| **API** | REST | REST | REST + GraphQL |
| **Migration from GitHub** | Yes | Yes | Yes |
| **Governance** | Corporate (Gitea Ltd) | Community (non-profit) | Corporate (GitLab Inc.) |

## Deployment: Docker Compose

### Gitea

```yaml
# docker-compose.yml for Gitea
services:
  gitea:
    image: gitea/gitea:1.23
    container_name: gitea
    restart: always
    environment:
      - USER_UID=1000
      - USER_GID=1000
      - GITEA__database__DB_TYPE=postgres
      - GITEA__database__HOST=db:5432
      - GITEA__database__NAME=gitea
      - GITEA__database__USER=gitea
      - GITEA__database__PASSWD=gitea_secret_pass
    volumes:
      - ./gitea-data:/data
      - /etc/timezone:/etc/timezone:ro
      - /etc/localtime:/etc/localtime:ro
    ports:
      - "3000:3000"
      - "222:22"
    depends_on:
      - db

  db:
    image: postgres:16-alpine
    container_name: gitea-db
    restart: always
    environment:
      - POSTGRES_USER=gitea
      - POSTGRES_PASSWORD=gitea_secret_pass
      - POSTGRES_DB=gitea
    volumes:
      - ./gitea-db:/var/lib/postgresql/data
```

Deploy with:
```bash
mkdir -p gitea-data gitea-db
docker compose up -d
```

Then visit `http://your-server:3000` to complete the initial setup wizard.

### Forgejo

```yaml
# docker-compose.yml for Forgejo
services:
  forgejo:
    image: codeberg.org/forgejo/forgejo:10
    container_name: forgejo
    restart: always
    environment:
      - USER_UID=1000
      - USER_GID=1000
      - FORGEO__database__DB_TYPE=postgres
      - FORGEO__database__HOST=db:5432
      - FORGEO__database__NAME=forgejo
      - FORGEO__database__USER=forgejo
      - FORGEO__database__PASSWD=forgejo_secret_pass
    volumes:
      - ./forgejo-data:/data
      - /etc/timezone:/etc/timezone:ro
      - /etc/localtime:/etc/localtime:ro
    ports:
      - "3000:3000"
      - "222:22"
    depends_on:
      - db

  db:
    image: postgres:16-alpine
    container_name: forgejo-db
    restart: always
    environment:
      - POSTGRES_USER=forgejo
      - POSTGRES_PASSWORD=forgejo_secret_pass
      - POSTGRES_DB=forgejo
    volumes:
      - ./forgejo-db:/var/lib/postgresql/data
```

The configuration is nearly identical to Gitea — just swap the image name. Deploy with:
```bash
mkdir -p forgejo-data forgejo-db
docker compose up -d
```

### GitLab CE

```yaml
# docker-compose.yml for GitLab CE
services:
  gitlab:
    image: gitlab/gitlab-ce:17
    container_name: gitlab
    restart: always
    hostname: git.example.com
    environment:
      GITLAB_OMNIBUS_CONFIG: |
        external_url 'https://git.example.com'
        gitlab_rails['gitlab_shell_ssh_port'] = 2222
        # Disable unused services to save resources
        prometheus_monitoring['enable'] = false
        nginx['redirect_http_to_https'] = true
        nginx['ssl_certificate'] = "/etc/gitlab/ssl/fullchain.pem"
        nginx['ssl_certificate_key'] = "/etc/gitlab/ssl/privkey.pem"
    ports:
      - "443:443"
      - "80:80"
      - "2222:22"
    volumes:
      - ./gitlab-config:/etc/gitlab
      - ./gitlab-logs:/var/log/gitlab
      - ./gitlab-data:/var/opt/gitlab
      - ./gitlab-ssl:/etc/gitlab/ssl:ro
    shm_size: '256m'
```

Deploy with:
```bash
mkdir -p gitlab-config gitlab-logs gitlab-data gitlab-ssl
docker compose up -d
# First start takes 3-5 minutes — be patient
```

Set the root password after the container is ready:
```bash
docker exec -it gitlab grep 'Password:' /etc/gitlab/initial_root_password
```

## Setting Up Reverse Proxy with Nginx

All three forges benefit from a reverse proxy for HTTPS termination. Here is a unified Nginx configuration:

```nginx
server {
    listen 443 ssl http2;
    server_name git.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/git.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/git.yourdomain.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Proxy to forge (adjust port as needed)
    location / {
        proxy_pass http://127.0.0.1:3000;  # Gitea/Forgejo
        # proxy_pass http://127.0.0.1:80;   # GitLab

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (needed for some features)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    client_max_body_size 500M;  # Allow large pushes
}
```

Get a free SSL certificate:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d git.yourdomain.com
```

## CI/CD Pipeline Setup

### Gitea / Forgejo Actions

Both support GitHub Actions-compatible workflows. Create `.gitea/workflows/ci.yml` in your repository:

```yaml
name: CI Pipeline
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run tests
        run: |
          pytest --cov=. --cov-report=xml

      - name: Build Docker image
        run: |
          docker build -t myapp:${{ github.sha }} .
```

Enable the actions runner on your server:
```bash
# For Gitea
docker run -d --name gitea-runner \
  -e GITEA_INSTANCE_URL=https://git.yourdomain.com \
  -e GITEA_RUNNER_REGISTRATION_TOKEN=your-token \
  -v /var/run/docker.sock:/var/run/docker.sock \
  gitea/act_runner:latest

# For Forgejo
docker run -d --name forgejo-runner \
  -e FORGEO_INSTANCE_URL=https://git.yourdomain.com \
  -e FORGEO_RUNNER_REGISTRATION_TOKEN=your-token \
  -v /var/run/docker.sock:/var/run/docker.sock \
  codeberg.org/forgejo/runner:latest
```

### GitLab CI

Create `.gitlab-ci.yml` at your repository root:

```yaml
stages:
  - test
  - build
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip
    - venv/

test:
  stage: test
  image: python:3.12-slim
  script:
    - pip install -r requirements.txt
    - pip install pytest pytest-cov
    - pytest --cov=. --cov-report=xml
  coverage: '/TOTAL.+ (\d+%)/'

build:
  stage: build
  image: docker:27
  services:
    - docker:27-dind
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  only:
    - main
```

## Migration from GitHub

Moving your existing GitHub repositories to a self-hosted forge is straightforward.

### Gitea / Forgejo Migration

1. Navigate to your instance URL and create an account
2. Click the **+** icon and select **New Migration**
3. Paste your GitHub repository URL
4. Enter your GitHub username and a personal access token
5. Select which items to migrate: issues, pull requests, labels, milestones, and releases
6. Click **Migrate Repository**

You can also migrate from the command line:
```bash
# Using the Gitea/Forgejo CLI
gitea admin repo migrate \
  --clone-url https://github.com/username/repo \
  --auth-username your-username \
  --auth-password your-token \
  --owner-name your-org \
  --repo-name repo \
  --mirror=false
```

### GitLab Migration

1. In GitLab, create a new project
2. Select **CI/CD for external repo** > **GitHub**
3. Authorize GitLab to access your GitHub account
4. Select repositories to import
5. GitLab imports code, issues, merge requests, and wiki pages

For bulk migration, use the `github-gitlab-importer` tool:
```bash
pip install python-gitlab
# Script to batch-migrate all repos from a GitHub org to GitLab
```

## Backup Strategy

A self-hosted forge is only as reliable as your backup plan.

### Gitea / Forgejo Backup

```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/gitea"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

# Database backup
docker exec gitea-db pg_dump -U gitea gitea | gzip > "$BACKUP_DIR/db_$TIMESTAMP.sql.gz"

# Data directory backup (repos, attachments, avatars)
tar czf "$BACKUP_DIR/data_$TIMESTAMP.tar.gz" -C /path/to gitea-data

# Keep only last 30 days of backups
find "$BACKUP_DIR" -type f -mtime +30 -delete

echo "Backup complete: $BACKUP_DIR"
```

Add a cron job to automate:
```bash
# Run daily at 2 AM
0 2 * * * /opt/scripts/backup-gitea.sh >> /var/log/gitea-backup.log 2>&1
```

### GitLab Backup

GitLab has a built-in backup command:
```bash
# Create backup
docker exec gitlab gitlab-backup create

# Restore from backup
docker exec gitlab gitlab-backup restore BACKUP=1712345678_2026_04_12_17.0.0

# Configure automated backups in gitlab.rb
gitlab_rails['manage_backup_path'] = true
gitlab_rails['backup_path'] = "/var/opt/gitlab/backups"
gitlab_rails['backup_keep_time'] = 604800  # 7 days in seconds
```

## Which Should You Choose?

### Choose Gitea if:
- You want the most mature, battle-tested lightweight forge
- You need excellent performance on minimal hardware
- You prefer a GitHub-like interface with no learning curve
- You do not mind corporate governance

### Choose Forgejo if:
- Community governance and open-source purity matter to you
- You want Fediverse integration (ActivityPub) out of the box
- You are concerned about Gitea's corporate direction
- You want a drop-in Gitea replacement with additional features

### Choose GitLab CE if:
- You need a complete DevOps platform, not just a Git forge
- Your team requires advanced CI/CD, security scanning, and compliance tools
- You have the infrastructure resources (8+ GB RAM per instance)
- You want built-in container registry, package registry, and monitoring

## Final Verdict

For most individuals and small teams in 2026, **Forgejo** represents the best balance of features, performance, and governance philosophy. It runs on a $5 VPS, supports GitHub Actions workflows, and gives you full control over your code without any corporate strings attached.

If you are already comfortable with Gitea and do not have governance concerns, Gitea remains an excellent choice — the codebase is mature and the user experience is polished.

GitLab CE is the pick for organizations that need an integrated DevOps platform and have the infrastructure to back it up. Nothing else comes close to its feature set, but the resource requirements are real.

No matter which you choose, the days of relying on a single corporate platform for all your source code are over. Self-hosting your Git forge gives you control, privacy, and peace of mind — and with modern Docker deployment, it has never been easier to set up.
