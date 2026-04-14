---
title: "Self-Hosted Package Registry: Nexus vs Verdaccio vs Pulp Guide 2026"
date: 2026-04-14
tags: ["comparison", "guide", "self-hosted", "privacy", "package-management"]
draft: false
description: "Complete guide to self-hosted package registries. Compare Sonatype Nexus, Verdaccio, and Pulp for npm, PyPI, Maven, Docker and more. Docker Compose setup, proxy caching, and production configuration for 2026."
---

## Why Self-Host Your Package Registry?

Every modern software project depends on external packages — npm modules, Python wheels, Maven artifacts, Docker images. Pulling these directly from public registries introduces real risks and costs that compound as your infrastructure grows.

- **Supply chain security** — public registries are frequent targets for typosquatting, dependency confusion, and malicious package injections. A private registry lets you audit and whitelist every dependency before it reaches your developers.
- **Build reliability** — public registries go down, throttle requests, and introduce latency. A local cache ensures builds complete in seconds even during npm or PyPI outages.
- **Bandwidth savings** — CI/CD pipelines can download gigabytes of dependencies per day. A local proxy cache eliminates redundant downloads and slashes internet bandwidth costs.
- **Private package distribution** — share internal libraries, custom-built artifacts, and proprietary modules across your organization without publishing them publicly.
- **Compliance and governance** — enforce license policies, track which versions are deployed where, and maintain an auditable record of every package in your stack.
- **Air-gapped environments** — teams working in restricted networks need a local source for all dependencies. A self-hosted registry makes offline development possible.

Whether you run a small homelab, a startup engineering team, or an enterprise CI/CD pipeline, a self-hosted package registry pays for itself in reliability alone. This guide covers the three most capable open-source options and walks you through production-ready deployments.

## Feature Comparison: Nexus vs Verdaccio vs Pulp

| Feature | Sonatype Nexus Repository | Verdaccio | Pulp Project |
|---------|---------------------------|-----------|--------------|
| **Package Formats** | 20+ (npm, PyPI, Maven, Docker, NuGet, RubyGems, Go, Helm, yum, apt, and more) | npm, Bower | 15+ (PyPI, Docker, rpm, deb, Ansible, Container, Maven, Rubygems, and more) |
| **Proxy Caching** | ✅ All formats | ✅ npm only | ✅ All formats |
| **Private Packages** | ✅ npm, PyPI, Maven, Docker, and more | ✅ npm only | ✅ All formats |
| **Proxy Upstream** | Multiple, configurable | npm registry | Multiple, configurable |
| **LDAP/AD Auth** | ✅ (Pro) / Basic (OSS) | ✅ via plugins | ✅ |
| **RBAC** | ✅ (Pro) / Basic (OSS) | ✅ via config | ✅ |
| **REST API** | ✅ Comprehensive | ✅ Basic | ✅ Comprehensive |
| **Docker Support** | ✅ Native (OSS) | ❌ | ✅ Native |
| **Storage Backend** | Local disk, S3 | Local disk, S3 (plugin) | S3, filesystem, Azure |
| **Cleanup Policies** | ✅ (Pro only) | ✅ via plugin | ✅ Native |
| **Language** | Java | Node.js | Python |
| **Memory Footprint** | ~2 GB minimum | ~150 MB | ~500 MB |
| **License** | EPL-1.0 (OSS), Commercial (Pro) | MIT | GPL-3.0 |
| **Best For** | Enterprise teams needing multi-format support | Node.js/npm-focused teams | Python/rpm/deb-heavy environments |

## Sonatype Nexus Repository Manager (OSS)

Nexus Repository Manager is the most mature and feature-complete open-source package registry available. The OSS edition supports proxy caching and hosting for over 20 package formats out of the box. It runs on the JVM and provides a polished web UI for browsing, searching, and managing artifacts.

### When to Choose Nexus

- Your team uses **multiple package ecosystems** (npm, Maven, PyPI, Docker) and wants one unified registry.
- You need **Docker registry** functionality alongside traditional package formats.
- You want a **battle-tested** solution used by thousands of enterprises worldwide.
- You can allocate at least 2 GB of RAM for the JVM process.

### Docker Compose Deployment

Create a `docker-compose.yml` for a production-ready Nexus instance:

```yaml
version: "3.8"

services:
  nexus:
    image: sonatype/nexus3:latest
    container_name: nexus-repo
    restart: unless-stopped
    ports:
      - "8081:8081"       # Web UI and API
      - "8082:8082"       # Docker registry (optional)
    volumes:
      - nexus-data:/nexus-data
      - ./nexus.props:/opt/sonatype/nexus/etc/nexus-default.properties:ro
    environment:
      - INSTALL4J_ADD_VM_PARAMS=-Xms512m -Xmx1024m -XX:MaxDirectMemorySize=512m
    networks:
      - repo-net

volumes:
  nexus-data:
    driver: local

networks:
  repo-net:
    driver: bridge
```

Create `nexus.props` to customize the default configuration:

```properties
nexus-args=${karaf.etc},${karaf.data}/etc,${karaf.data}/etc,${nexus.data}/etc
nexus-edition=nexus-pro-edition
application-port=8081
application-host=0.0.0.0
```

Start the service:

```bash
docker compose up -d
```

The first startup takes 2–3 minutes as Nexus initializes its databases. Find the admin password with:

```bash
docker exec nexus-repo cat /nexus-data/admin.password
```

### Configuring npm Proxy Cache

After logging in with the admin credentials, create a proxy repository:

1. Go to **Administration → Repositories → Create repository**
2. Select **npm (proxy)**
3. Set the name to `npm-proxy`
4. Set Remote storage to `https://registry.npmjs.org`
5. Under **Storage**, set Blob store to `default`
6. Under **HTTP**, enable **Use trust store** if your organization uses a proxy
7. Save the repository

Then create an **npm (group)** repository that combines `npm-proxy` with any hosted npm repositories you create for private packages. This group repository becomes your single npm endpoint.

Configure npm clients to use your registry:

```bash
npm set registry http://nexus-server:8081/repository/npm-group/
```

For a project-level configuration, add to `.npmrc`:

```
registry=http://nexus-server:8081/repository/npm-group/
```

### Configuring PyPI Proxy Cache

The process mirrors the npm setup:

1. **Administration → Repositories → Create repository → pypi (proxy)**
2. Set Remote storage to `https://pypi.org`
3. Name it `pypi-proxy`
4. Save

Create a **pypi (group)** repository combining the proxy with any hosted repositories. Then configure pip:

```bash
pip config set global.index-url http://nexus-server:8081/repository/pypi-group/simple
pip config set global.trusted-host nexus-server
```

Or use a project-level `pip.conf`:

```ini
[global]
index-url = http://nexus-server:8081/repository/pypi-group/simple
trusted-host = nexus-server
```

### Docker Registry Setup

Nexus OSS supports Docker registries natively. Create three repositories:

1. **docker (proxy)** — pointing to `https://registry-1.docker.io`
2. **docker (hosted)** — for private images
3. **docker (group)** — combining both

Configure the HTTP connector on port 8082 in the docker group repo settings. Then pull through your proxy:

```bash
docker login nexus-server:8082
docker pull nexus-server:8082/library/nginx:latest
```

Add to `/etc/docker/daemon.json` to allow insecure registry access on your network:

```json
{
  "insecure-registries": ["nexus-server:8082"]
}
```

## Verdaccio — Lightweight npm Registry

Verdaccio is a purpose-built npm registry written in Node.js. It is significantly lighter than Nexus, starts in seconds, and uses minimal resources. If your team works exclusively with npm packages, Verdaccio is the simplest and most focused option.

### When to Choose Verdaccio

- Your stack is **primarily or exclusively Node.js/npm**.
- You want a **lightweight** service that runs on a Raspberry Pi or low-end VPS.
- You value **simplicity** — a single YAML config file controls everything.
- You need **uplinks** to multiple npm registries (npmjs, GitHub Packages, etc.).

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  verdaccio:
    image: verdaccio/verdaccio:5
    container_name: verdaccio
    restart: unless-stopped
    ports:
      - "4873:4873"
    volumes:
      - ./conf:/verdaccio/conf
      - ./storage:/verdaccio/storage
      - ./plugins:/verdaccio/plugins
    environment:
      - VERDACCIO_PORT=4873
    networks:
      - repo-net

networks:
  repo-net:
    driver: bridge
```

Create `conf/config.yaml`:

```yaml
storage: /verdaccio/storage
plugins: /verdaccio/plugins

uplinks:
  npmjs:
    url: https://registry.npmjs.org/
    timeout: 10s
    maxage: 2m
    max_fails: 3
    fail_timeout: 2m
  github:
    url: https://npm.pkg.github.com/
    timeout: 10s
    headers:
      Authorization: "Bearer ${GITHUB_TOKEN}"

packages:
  "@*/*":
    access: $all
    publish: $authenticated
    proxy: npmjs github

  "**":
    access: $all
    publish: $authenticated
    proxy: npmjs github

log:
  type: stdout
  format: pretty
  level: http

auth:
  htpasswd:
    file: /verdaccio/conf/htpasswd
    max_users: 100

middlewares:
  audit:
    enabled: true

listen: 0.0.0.0:4873
```

This configuration:

- Proxies requests to both npmjs and GitHub Packages as uplinks
- Caches packages for 2 minutes before revalidating
- Allows anyone to read packages but requires authentication to publish
- Enables audit middleware for `npm audit` support
- Limits to 100 local user accounts (sufficient for most teams)

Start and create your first user:

```bash
docker compose up -d
npm adduser --registry http://localhost:4873
```

### Publishing Private Packages

After creating a user account, publish a private package:

```bash
cd your-npm-package
npm publish --registry http://localhost:4873
```

To scope your packages under an organization-like namespace:

```json
{
  "name": "@myteam/utils",
  "version": "1.0.0",
  "publishConfig": {
    "registry": "http://localhost:4873"
  }
}
```

### Advanced: S3 Storage Backend

For production deployments, store packages on S3 instead of local disk. Install the plugin:

```bash
npm install -g verdaccio-aws-s3-storage
```

Then update `config.yaml`:

```yaml
storage:
  s3:
    bucket: verdaccio-packages
    keyPrefix: packages/
    region: us-east-1
    accessKeyId: ${AWS_ACCESS_KEY_ID}
    secretAccessKey: ${AWS_SECRET_ACCESS_KEY}
```

## Pulp Project — Python-Native Multi-Format Registry

Pulp is a platform for managing software repositories, written in Python. It supports a wide range of package formats through a plugin architecture and integrates particularly well with Python and Linux distribution ecosystems.

### When to Choose Pulp

- Your infrastructure is **Python-heavy** and you need PyPI proxy caching with fine-grained control.
- You manage **Linux distribution packages** (rpm, deb) and need repository mirroring.
- You want **Ansible content** (collections, roles) hosting alongside other formats.
- You prefer a **Python-based** stack that integrates with your existing tooling.

### Docker Compose Deployment

Pulp uses a multi-container architecture with a resource manager, worker, content server, and Redis:

```yaml
version: "3.8"

services:
  pulp:
    image: pulp/pulp:latest
    container_name: pulp
    restart: unless-stopped
    ports:
      - "8080:80"
      - "443:443"
    environment:
      - PULP_ADMIN_USER=admin
      - PULP_ADMIN_PASSWORD=admin
    volumes:
      - pulp-settings:/etc/pulp
      - pulp-data:/var/lib/pulp/media
    networks:
      - repo-net

volumes:
  pulp-settings:
  pulp-data:

networks:
  repo-net:
    driver: bridge
```

Start the stack:

```bash
docker compose up -d
```

After the containers initialize (about 60 seconds), access the API:

```bash
export PULP_BASE_URL=http://localhost:8080
export PULP_USERNAME=admin
export PULP_PASSWORD=admin
```

### Setting Up a PyPI Remote and Repository

Pulp uses a remote/repository/publication/distribution model. The **remote** defines the upstream source, the **repository** stores synced content, the **publication** creates a snapshot, and the **distribution** serves it to clients.

Sync from PyPI:

```bash
pulp rpm remote create --name pypi-remote --url https://pypi.org/
pulp rpm repository create --name pypi-local --remote pypi-remote
pulp rpm repository sync --name pypi-local
```

For PyPI specifically, use the pulp-python plugin:

```bash
pulp python remote create --name pypi-remote --url https://pypi.org/
pulp python repository create --name pypi-local --remote pypi-remote
pulp python repository sync --name pypi-local
pulp python publication create --repository pypi-local
pulp python distribution create --name pypi-dist --base-path pypi --repository pypi-local
```

Configure pip to use your Pulp instance:

```bash
pip install --index-url http://localhost:8080/pulp/content/pypi-dist/simple/ requests
```

### Mirroring a Docker Registry

Pulp can mirror Docker registries for offline access:

```bash
pulp container remote create --name dockerhub-nginx \
  --url https://registry-1.docker.io \
  --include-tags nginx:latest,nginx:1.25,nginx:alpine

pulp container repository create --name nginx-local \
  --remote dockerhub-nginx

pulp container repository sync --name nginx-local
pulp container distribution create --name nginx-dist \
  --base-path nginx --repository nginx-local
```

Pull images through your local mirror:

```bash
docker pull localhost:8080/pulp/content/nginx-dist/nginx:alpine
```

### Scheduled Sync Tasks

Keep your local mirrors up to date with scheduled syncs:

```bash
# Sync every 6 hours
pulp task-schedule create \
  --name pypi-daily-sync \
  --task "pulpcore.app.tasks.repository.sync" \
  --schedule "0 */6 * * *" \
  --repository pypi-local
```

## Putting It All Together: Reverse Proxy and HTTPS

Regardless of which registry you choose, putting it behind a reverse proxy with HTTPS is essential for production use. Here is a Caddy configuration that handles TLS automatically:

```caddyfile
registry.example.com {
    reverse_proxy localhost:8081

    tls admin@example.com

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
    }
}
```

Or with Nginx and Let's Encrypt:

```nginx
server {
    listen 443 ssl http2;
    server_name registry.example.com;

    ssl_certificate /etc/letsencrypt/live/registry.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/registry.example.com/privkey.pem;

    client_max_body_size 500M;

    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Obtain the certificate with Certbot:

```bash
certbot certonly --nginx -d registry.example.com
```

## Migration Checklist

Moving from public registries to a self-hosted proxy requires coordination:

1. **Deploy** your registry on a reliable server with adequate storage (start with 50 GB for npm, 100 GB for multi-format).
2. **Configure proxy upstreams** for each package format your team uses.
3. **Test** by pointing a single non-critical project at your registry and verifying that installs work.
4. **Update CI/CD pipelines** — modify your pipeline configuration to use the local registry. For GitHub Actions:

```yaml
- name: Setup npm registry
  run: npm config set registry http://nexus-server:8081/repository/npm-group/

- name: Setup pip
  run: pip config set global.index-url http://nexus-server:8081/repository/pypi-group/simple
```

5. **Distribute configuration** — use an `.npmrc`, `pip.conf`, or `.m2/settings.xml` checked into each repository so developers get the correct registry automatically.
6. **Monitor disk usage** — set up alerts when storage exceeds 80% capacity. Configure cleanup policies to remove old cached packages.
7. **Backup regularly** — back up the data volume and configuration files. For Nexus:

```bash
docker exec nexus-repo tar czf /tmp/nexus-backup-$(date +%F).tar.gz /nexus-data
docker cp nexus-repo:/tmp/nexus-backup-*.tar.gz ./backups/
```

## Choosing the Right Tool

- **Choose Nexus** if you need a single registry for npm, Maven, PyPI, Docker, and more. It is the most versatile option and the industry standard for multi-format repositories.
- **Choose Verdaccio** if you only need npm. It starts in seconds, uses under 200 MB of RAM, and its configuration is a single readable YAML file.
- **Choose Pulp** if you work heavily with Python packages, Linux distribution repositories, or Ansible content. Its Python-native architecture and plugin system make it highly extensible.

All three are production-ready, open-source, and free to run. The best choice depends on your team's primary package ecosystems and infrastructure constraints. Set one up this weekend and your next dependency outage will be a non-event.
