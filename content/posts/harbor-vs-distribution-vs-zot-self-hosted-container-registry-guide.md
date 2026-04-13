---
title: "Best Self-Hosted Container Registry 2026: Harbor vs CNCF Distribution vs Zot"
date: 2026-04-13
tags: ["comparison", "guide", "self-hosted", "docker", "containers", "devops"]
draft: false
description: "Compare the top self-hosted container registries in 2026: Harbor, CNCF Distribution, and Zot. Full Docker Compose setups, security configuration, and a side-by-side feature comparison for homelabs and production environments."
---

## Why Self-Host a Container Registry?

If you run Docker containers — whether for a homelab, a small team, or a production environment — you eventually hit the limits of Docker Hub. Rate limits, image size restrictions, privacy concerns, and dependency on an external service make a self-hosted container registry one of the most practical infrastructure decisions you can make.

Here's what you gain by running your own registry:

**No rate limits.** Docker Hub's free tier caps anonymous pulls at 100 per 6 hours and authenticated pulls at 200 per 6 hours. A self-hosted registry has zero pull limits — your only bottleneck is network bandwidth.

**Full image privacy.** Your proprietary application images, internal tooling, and custom base images never leave your network. This matters for compliance (SOC 2, HIPAA, GDPR) and for protecting intellectual property.

**Faster pulls.** When your registry lives on the same LAN or data center as your compute nodes, image pulls happen at local network speeds. A 2 GB image that takes 30 seconds from Docker Hub might pull in under 3 seconds locally.

**Complete control over retention and cleanup.** Set your own policies for how many image tags to keep, when to delete untagged manifests, and how long to retain pull logs. No vendor-imposed quotas.

**Cost predictability.** Docker Hub Pro costs $60/user/year with storage limits. Harbor, Distribution, and Zot are all free and open-source — you only pay for the disk and compute you provision.

In 2026, three projects stand out in the self-hosted container registry space: **Harbor** (the enterprise-grade platform from VMware/CNCF), **CNCF Distribution** (the minimal, composable registry that powers Docker Hub itself), and **Zot** (the modern OCI-native registry with built-in security scanning). Let's compare them.

## Quick Comparison Table

| Feature | Harbor | CNCF Distribution | Zot |
|---------|--------|-------------------|-----|
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| **Written In** | Go + Vue.js (UI) | Go | Go |
| **OCI Compliant** | ✅ | ✅ (originator) | ✅ Native |
| **Web UI** | ✅ Full-featured | ❌ None | ✅ Basic |
| **RBAC** | ✅ Project-based, LDAP/AD/OIDC | ❌ Basic auth only | ✅ OIDC, htpasswd |
| **Image Scanning** | ✅ Trivy, Clair | ❌ Plugin required | ✅ Built-in Trivy |
| **Replication** | ✅ To other registries | ❌ Manual | ✅ Pull/Push |
| **Content Trust** | ✅ Notary integration | ❌ Not supported | ✅ Cosign support |
| **Helm Charts** | ✅ Native support | ❌ | ❌ |
| **Proxy Cache** | ✅ Cache Docker Hub, GHCR, etc. | ✅ Via registry-mirror | ✅ Via upstream config |
| **Min RAM** | ~2 GB | ~64 MB | ~128 MB |
| **Docker Compose** | ✅ Official compose file | ✅ Simple config | ✅ Single binary |
| **Garbage Collection** | ✅ Online GC | ✅ Online GC | ✅ Online GC |
| **API** | ✅ REST + Swagger | ✅ REST | ✅ REST + OpenAPI |
| **Best For** | Enterprises, teams | Minimal setups, embedded | Security-focused teams |

## Harbor: The Enterprise Registry Platform

Harbor is the most feature-complete container registry available as open-source software. Originally developed by VMware and now a graduated CNCF project, Harbor is the registry of choice for organizations that need role-based access control, image vulnerability scanning, audit logging, and replication out of the box.

### When to Choose Harbor

Harbor makes sense when you need more than just a place to push and pull images. It's ideal for:

- Teams managing dozens of projects with different access policies
- Organizations that require vulnerability scanning before deployment
- Environments that need to replicate images across multiple registry instances (e.g., edge deployments)
- Anyone who wants a full web UI for browsing, searching, and managing container images

### Architecture

Harbor is a multi-service architecture. A typical deployment includes:

- **Core** — the main API and web UI server
- **Jobservice** — handles replication, scanning, and garbage collection jobs
- **Registry** — the underlying CNCF Distribution instance for actual image storage
- **Portal** — the Vue.js frontend
- **Database** — PostgreSQL for metadata (users, projects, RBAC, scan results)
- **Redis** — caching and session management
- **Trivy** — optional container image vulnerability scanner

This means Harbor has more moving parts than the alternatives, but each component is production-grade and horizontally scalable.

### Installation with Docker Compose

Harbor provides an official installer that generates a complete Docker Compose configuration. Here's the recommended setup for a production homelab or small team:

```bash
# Download and extract Harbor
HARBOR_VERSION="v2.12.2"
wget "https://github.com/goharbor/harbor/releases/download/${HARBOR_VERSION}/harbor-offline-installer-${HARBOR_VERSION}.tgz"
tar -xzf "harbor-offline-installer-${HARBOR_VERSION}.tgz"
cd harbor

# Edit the configuration
cat > harbor.yml << 'EOF'
hostname: registry.example.com
http:
  port: 8080
https:
  port: 8443
  certificate: /data/cert/server.crt
  private_key: /data/cert/server.key
harbor_admin_password: ChangeMeNow2026!
database:
  password: db_password_secure
  max_idle_conns: 100
  max_open_conns: 900
data_volume: /opt/harbor/data
trivy:
  ignore_unfixed: false
  skip_update: false
  offline_scan: false
  insecure: false
jobservice:
  max_job_workers: 10
notification:
  webhook_job_max_retry: 10
log:
  level: info
  local:
    rotate_count: 50
    rotate_size: 200M
    location: /var/log/harbor
proxy:
  http_proxy:
  https_proxy:
  no_proxy:
  components:
    - core
    - jobservice
    - trivy
EOF

# Install with HTTPS enabled
./install.sh --with-trivy --with-chartmuseum
```

For a lightweight homelab setup without HTTPS (behind a reverse proxy):

```yaml
# docker-compose.harbor.yml
services:
  harbor-core:
    image: goharbor/harbor-core:v2.12.2
    restart: unless-stopped
    depends_on:
      - harbor-db
      - harbor-redis
    environment:
      - CORE_SECRET=your_core_secret_key
      - PORT=8080
    volumes:
      - /opt/harbor/config:/etc/core:ro
    networks:
      - harbor-net

  registry:
    image: goharbor/registry-photon:v2.12.2
    restart: unless-stopped
    volumes:
      - /opt/harbor/data/registry:/storage:z
    networks:
      - harbor-net

  harbor-db:
    image: goharbor/harbor-db:v2.12.2
    restart: unless-stopped
    environment:
      - POSTGRESQL_PASSWORD=db_password_secure
    volumes:
      - /opt/harbor/data/database:/var/lib/postgresql/data
    networks:
      - harbor-net

  harbor-redis:
    image: goharbor/redis-photon:v2.12.2
    restart: unless-stopped
    networks:
      - harbor-net

  trivy:
    image: goharbor/trivy-adapter-photon:v2.12.2
    restart: unless-stopped
    volumes:
      - /opt/harbor/data/trivy:/home/scanner/.cache/trivy
    networks:
      - harbor-net

networks:
  harbor-net:
    driver: bridge
```

After starting with `docker compose -f docker-compose.harbor.yml up -d`, access the web UI at `http://your-server:8080` and log in with `admin` / your configured password.

### Configuring Proxy Cache for Docker Hub

One of Harbor's most useful features is the proxy cache. Instead of hitting Docker Hub rate limits, Harbor caches every pulled image locally:

1. Log into the Harbor web UI as admin
2. Navigate to **Registries** > **New Endpoint**
3. Set provider to **Docker Hub**, enter credentials
4. Navigate to **Projects** > **New Project**, enable **Proxy Cache**, select your Docker Hub endpoint
5. Pull via your Harbor: `docker pull harbor.example.com/dockerhub/library/nginx:latest`

Harbor now caches every image pulled through this project. Subsequent pulls of the same tag hit Harbor's local cache instantly.

## CNCF Distribution: The Minimal Registry

CNCF Distribution (formerly Docker Distribution) is the reference implementation of the OCI Distribution Specification. It's the simplest, most lightweight option — a single binary that serves as a Docker-compatible registry with minimal dependencies.

### When to Choose Distribution

Distribution is the right choice when you want:

- A dead-simple registry with zero ceremony
- Minimal resource footprint (runs comfortably on a Raspberry Pi)
- The exact same technology that powers Docker Hub and GitHub Container Registry
- A registry to embed into another application or pipeline
- No web UI, no database, no scanning — just push and pull

### Installation with Docker Compose

Distribution can run as a single container with a simple configuration file:

```yaml
# docker-compose.distribution.yml
services:
  registry:
    image: registry:2
    container_name: distribution-registry
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - /opt/registry/data:/var/lib/registry
      - /opt/registry/config/config.yml:/etc/distribution/config.yml:ro
      - /opt/registry/certs:/certs:ro
    environment:
      - REGISTRY_HTTP_ADDR=0.0.0.0:5000
      - REGISTRY_HTTP_TLS_CERTIFICATE=/certs/domain.crt
      - REGISTRY_HTTP_TLS_KEY=/certs/domain.key
      - REGISTRY_STORAGE_DELETE_ENABLED=true
      - REGISTRY_LOG_LEVEL=info
```

Minimal configuration file (`/opt/registry/config/config.yml`):

```yaml
version: 0.1
log:
  fields:
    service: registry
storage:
  cache:
    blobdescriptor: inmemory
  filesystem:
    rootdirectory: /var/lib/registry
  delete:
    enabled: true
http:
  addr: :5000
  headers:
    X-Content-Type-Options: [nosniff]
  tls:
    certificate: /certs/domain.crt
    key: /certs/domain.key
auth:
  htpasswd:
    realm: "Registry Realm"
    path: /etc/distribution/htpasswd
health:
  storagedriver:
    enabled: true
    interval: 10s
    threshold: 3
```

Generate the htpasswd file for basic authentication:

```bash
mkdir -p /opt/registry/certs /opt/registry/config

# Install htpasswd utility (if not available)
apt-get install -y apache2-utils

# Create user credentials
htpasswd -Bbn devuser "SecurePass2026!" > /opt/registry/config/htpasswd

# Generate self-signed TLS certs for testing
openssl req -x509 -newkey rsa:4096 \
  -keyout /opt/registry/certs/domain.key \
  -out /opt/registry/certs/domain.crt \
  -days 365 -nodes \
  -subj "/CN=registry.example.com"

# Start the registry
docker compose -f docker-compose.distribution.yml up -d
```

To use the registry from your Docker client, configure the daemon to trust the registry's CA certificate:

```bash
# Copy the CA cert to Docker's trusted store
sudo mkdir -p /etc/docker/certs.d/registry.example.com:5000
sudo cp /opt/registry/certs/domain.crt \
  /etc/docker/certs.d/registry.example.com:5000/ca.crt

# Restart Docker
sudo systemctl restart docker

# Login and push
docker login registry.example.com:5000
docker tag myapp:latest registry.example.com:5000/myapp:latest
docker push registry.example.com:5000/myapp:latest
```

### Adding Garbage Collection

Distribution supports garbage collection to reclaim disk space from deleted images. Run it periodically via a cron job:

```bash
# Garbage collect weekly
0 3 * * 0 docker exec distribution-registry registry garbage-collect /etc/distribution/config.yml --delete-untagged
```

## Zot: The OCI-Native Security Registry

Zot is a modern, OCI-native container registry built from the ground up with security in mind. Developed by Project Zot (a CNCF sandbox project), it offers built-in image scanning with Trivy, fine-grained access control, and a clean web UI — all in a single binary with no external database dependencies.

### When to Choose Zot

Zot is a great fit when you want:

- Built-in vulnerability scanning without deploying a separate scanner
- Cosign-based content trust and signature verification
- A single-binary deployment that's easy to manage
- OCI-native features like referrers API and artifact manifests
- Fine-grained authorization policies without the complexity of Harbor

### Installation with Docker Compose

Zot runs as a single process with a YAML configuration file. Here's a production-ready setup:

```yaml
# docker-compose.zot.yml
services:
  zot:
    image: ghcr.io/project-zot/zot:v2.1.0
    container_name: zot-registry
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - /opt/zot/data:/var/lib/registry
      - /opt/zot/config/config.json:/etc/zot/config.json:ro
    environment:
      - ZOT_LOG_LEVEL=info
```

Configuration file (`/opt/zot/config/config.json`):

```json
{
  "distSpecVersion": "1.1.0",
  "storage": {
    "rootDirectory": "/var/lib/registry",
    "dedupe": true,
    "remoteCache": true,
    "gc": true,
    "gcDelay": "1h",
    "gcInterval": "24h",
    "subPaths": {
      "/project-a": {
        "rootDirectory": "/var/lib/registry/project-a",
        "dedupe": true
      },
      "/project-b": {
        "rootDirectory": "/var/lib/registry/project-b",
        "dedupe": true
      }
    }
  },
  "http": {
    "address": "0.0.0.0",
    "port": "5000",
    "realm": "Zot Registry",
    "tls": {
      "cert": "/etc/zot/certs/server.crt",
      "key": "/etc/zot/certs/server.key"
    }
  },
  "log": {
    "level": "info",
    "output": "/var/log/zot.log"
  },
  "auth": {
    "htpasswd": {
      "path": "/etc/zot/htpasswd"
    },
    "failDelay": 5
  },
  "accessControl": {
    "repositories": {
      "**": {
        "policies": [
          {
            "users": ["admin"],
            "actions": ["read", "create", "update", "delete"]
          },
          {
            "users": ["developer"],
            "actions": ["read", "create"]
          },
          {
            "users": ["viewer"],
            "actions": ["read"]
          }
        ],
        "defaultPolicy": []
      }
    },
    "adminPolicy": {
      "users": ["admin"],
      "actions": ["read", "create", "update", "delete"]
    }
  },
  "extensions": {
    "search": {
      "enable": true,
      "cve": {
        "updateInterval": "24h"
      }
    },
    "scrub": {
      "enable": true,
      "interval": "24h"
    },
    "ui": {
      "enable": true
    },
    "sync": {
      "credentialsFile": "/etc/zot/sync-credentials.json",
      "registries": [
        {
          "urls": ["https://registry-1.docker.io"],
          "pollInterval": "6h",
          "content": [
            {
              "prefix": "library/nginx",
              "tags": {
                "semver": true
              }
            },
            {
              "prefix": "library/alpine",
              "tags": {
                "regex": "3\\.\\d+\\.\\d+"
              }
            }
          ]
        }
      ]
    }
  }
}
```

Set up and start Zot:

```bash
mkdir -p /opt/zot/{data,config,logs} /opt/zot/certs

# Generate TLS certificates
openssl req -x509 -newkey rsa:4096 \
  -keyout /opt/zot/certs/server.key \
  -out /opt/zot/certs/server.crt \
  -days 365 -nodes \
  -subj "/CN=registry.example.com"

# Create htpasswd file
apt-get install -y apache2-utils
htpasswd -Bbn admin "AdminPass2026!" > /opt/zot/config/htpasswd
htpasswd -Bbn developer "DevPass2026!" >> /opt/zot/config/htpasswd
htpasswd -Bbn viewer "ViewPass2026!" >> /opt/zot/config/htpasswd

# Create sync credentials (if mirroring Docker Hub)
cat > /opt/zot/config/sync-credentials.json << 'EOF'
{
  "registries": [
    {
      "url": "https://registry-1.docker.io",
      "username": "your-dockerhub-user",
      "password": "your-dockerhub-password"
    }
  ]
}
EOF

# Start Zot
docker compose -f docker-compose.zot.yml up -d
```

Access the web UI at `https://registry.example.com:5000` — Zot's built-in interface lets you browse repositories, view image tags, inspect manifests, and see CVE scan results without any additional setup.

### Built-in Image Scanning

Zot's standout feature is its integrated Trivy scanner. Unlike Harbor (which requires a separate Trivy container), Zot runs scanning as a built-in extension. It automatically scans every pushed image and surfaces vulnerabilities directly in the web UI and API:

```bash
# Check scan results via API
curl -s -u admin:AdminPass2026! \
  https://registry.example.com:5000/v2/_zot/ext/monitor | jq .

# View CVE details for a specific image
curl -s -u admin:AdminPass2026! \
  "https://registry.example.com:5000/v2/myapp/manifests/latest" \
  -H "Accept: application/vnd.oci.image.manifest.v1+json" | jq .
```

## Detailed Feature Breakdown

### Security

| Aspect | Harbor | Distribution | Zot |
|--------|--------|-------------|-----|
| **Authentication** | LDAP, AD, OIDC, DB | htpasswd, token | htpasswd, OIDC, LDAP |
| **Authorization** | RBAC per project | Basic | Policy-based ACL |
| **Image Scanning** | Trivy, Clair (separate) | None built-in | Trivy (built-in) |
| **Content Trust** | Notary v1/v2 | Not supported | Cosign, Notation |
| **Audit Logging** | ✅ Full audit trail | ❌ | ✅ Basic |
| **TLS** | ✅ Mutual TLS support | ✅ | ✅ |
| **SBOM Generation** | ✅ Via Trivy | ❌ | ✅ Built-in |

### Developer Experience

| Aspect | Harbor | Distribution | Zot |
|--------|--------|-------------|-----|
| **Web UI** | Full project management | None | Browse, search, CVE view |
| **API** | REST + Swagger docs | REST | REST + OpenAPI |
| **CLI** | `harbor-cli` (community) | `reg` (third-party) | `zot` (limited) |
| **Helm Support** | ✅ Native chart repo | ❌ | ❌ |
| **Proxy Cache** | ✅ Multi-source | Via mirror config | ✅ Sync extension |
| **Replication** | ✅ Push/Pull to remote | ❌ | ✅ Pull from upstream |

### Operational Requirements

| Aspect | Harbor | Distribution | Zot |
|--------|--------|-------------|-----|
| **Min RAM** | ~2 GB | ~64 MB | ~128 MB |
| **Containers** | 6-8 services | 1 container | 1 container |
| **External DB** | PostgreSQL required | None | None |
| **External Cache** | Redis required | None | None |
| **Disk for 100 images** | ~5 GB + DB overhead | ~4 GB | ~4 GB |
| **Upgrade complexity** | Multi-service upgrade | Single binary swap | Single binary swap |
| **Backup** | DB + registry storage | Registry storage only | Registry storage only |

## Choosing the Right Registry

The decision comes down to your team size, security requirements, and operational tolerance:

**Pick Harbor if** you're running a team or organization that needs the full platform experience — user management, project-scoped permissions, vulnerability scanning, replication across sites, and Helm chart hosting. The operational overhead of managing 6-8 containers is justified by the feature set. Harbor is what you run when Docker Hub isn't enough but you still want everything in one place.

**Pick CNCF Distribution if** you want the absolute simplest registry possible. It's a single container, a config file, and a data directory. No database, no Redis, no UI, no scanning. Just `docker push` and `docker pull`. This is perfect for homelab users who need a private registry for personal projects, CI pipelines that build and consume images on the same machine, or embedded use cases where you ship a registry as part of a larger product.

**Pick Zot if** you want a middle ground — single-binary simplicity with modern security features built in. Zot's integrated Trivy scanning, Cosign signature verification, and fine-grained access control give you enterprise-grade capabilities without Harbor's operational complexity. The built-in web UI and sync extension (for mirroring upstream registries) make it a compelling choice for small-to-medium teams that care about supply chain security.

## Practical Recommendations

For a **homelab with 1-2 users**: Start with CNCF Distribution. It takes 5 minutes to set up, uses negligible resources, and does exactly what you need. Add Zot later if you want scanning and a web UI.

For a **small team (5-20 people)**: Zot hits the sweet spot. You get vulnerability scanning, role-based access, a web UI, and sync capabilities — all in a single container with no database to manage.

For a **larger team or organization**: Harbor is worth the operational investment. The project-based RBAC, replication, Helm support, and audit logging solve real problems that Zot and Distribution simply don't address.

No matter which you choose, running your own container registry in 2026 means faster builds, zero rate limits, full data sovereignty, and no surprises on your monthly cloud bill. The setup is straightforward, the maintenance is minimal, and the benefits compound with every image you push.
