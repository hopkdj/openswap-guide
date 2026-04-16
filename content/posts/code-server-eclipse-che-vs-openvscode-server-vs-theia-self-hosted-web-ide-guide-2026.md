---
title: "Code-Server vs Eclipse Che vs OpenVSCode Server: Best Self-Hosted Web IDE 2026"
date: 2026-04-16
tags: ["comparison", "guide", "self-hosted", "developer-tools"]
draft: false
description: "Complete guide to running VS Code and other IDEs in the browser. Compare code-server, Eclipse Che, OpenVSCode Server, and Theia for remote development in 2026."
---

Developing software from any device, anywhere, without installing anything locally — that's the promise of self-hosted web IDEs. Instead of relying on expensive cloud services like GitHub Codespaces or Gitpod, you can run your own browser-based development environment on a cheap VPS, a home server, or even a Raspberry Pi.

In 2026, the landscape of self-hosted web IDEs has matured significantly. Four major options dominate this space: **code-server**, **OpenVSCode Server**, **Eclipse Che**, and **Theia**. Each takes a different approach to delivering a full-featured development experience through a web browser.

This guide breaks down how they differ, how to deploy them, and which one fits your workflow.

## Why Self-Host Your IDE?

Running a web-based IDE on your own infrastructure offers several advantages over cloud-hosted alternatives:

- **Full control over the environment**: Install any language runtime, SDK, or system dependency without restrictions. You're not limited by a cloud provider's pre-built images.
- **Data privacy**: Your source code, credentials, and development artifacts never leave your server. This matters for proprietary codebases or regulated environments.
- **Cost efficiency**: A $6/month VPS can replace a $25/month GitHub Codespaces subscription. Home servers cost nothing beyond electricity.
- **Persistent workspaces**: Unlike ephemeral cloud environments, your workspace state, extensions, and terminal history survive across sessions.
- **Custom infrastructure**: Connect to internal databases, message queues, and staging environments that aren't reachable from public cloud providers.
- **Offline-capable sync**: Set up your own workspace that persists regardless of third-party service availability.

Whether you're a developer who wants to code from an iPad, a team that needs consistent environments, or a homelab enthusiast building a complete self-hosted dev stack — a web IDE is a practical foundation.

## Option 1: code-server — VS Code in the Browser

**code-server** (by Coder) is the most popular way to run Visual Studio Code in a browser. It packages the open-source VS Code editor with a backend that handles file access, terminal sessions, and extension management over HTTP.

### Key Features

- Near-identical experience to desktop VS Code
- Full extension marketplace support
- Integrated terminal with SSH capabilities
- Password and token-based authentication
- Let's Encrypt certificate support built in
- Active community and extensive documentation

### Docker Deployment

```yaml
version: "3.8"
services:
  code-server:
    image: lscr.io/linuxserver/code-server:latest
    container_name: code-server
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=America/New_York
      - PASSWORD=your-secure-password
      - DEFAULT_WORKSPACE=/config/workspace
    volumes:
      - ./config:/config
      - ./workspace:/config/workspace
    ports:
      - 8443:8443
    restart: unless-stopped
```

For a reverse proxy setup with Nginx:

```nginx
server {
    listen 443 ssl;
    server_name ide.example.com;

    ssl_certificate /etc/letsencrypt/live/ide.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ide.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8443;
        proxy_set_header Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Quick Start Without Docker

```bash
curl -fsSL https://code-server.dev/install.sh | sh
code-server --bind-addr 0.0.0.0:8080 --auth password
```

The password can be set via the `PASSWORD` environment variable or stored in `~/.config/code-server/config.yaml`.

### Pros and Cons

| Pros | Cons |
|------|------|
| Best VS Code compatibility | Tied to VS Code's architecture — can't customize the shell |
| Mature and well-documented | Linuxserver fork diverges from upstream occasionally |
| Easy to deploy | Resource-heavy compared to lighter editors |
| Excellent extension support | Single-user by default; multi-user needs workarounds |

## Option 2: OpenVSCode Server — Gitpod's VS Code Fork

**OpenVSCode Server** is Gitpod's fork of VS Code, designed to run VS Code on a remote machine and access it through a web browser. Unlike code-server, it tracks the official VS Code releases more closely and is maintained by Gitpod.

### Key Features

- Close tracking of upstream VS Code releases
- Built by Gitpod with production-grade reliability
- Clean separation of frontend and backend
- Supports the same extension marketplace as desktop VS Code
- Simpler architecture than code-server

### Docker Deployment

```yaml
version: "3.8"
services:
  openvscode-server:
    image: gitpod/openvscode-server:latest
    container_name: openvscode-server
    user: "1000:1000"
    environment:
      - CONNECTION_TOKEN=your-secret-token
    volumes:
      - ./workspace:/home/workspace:cached
      - ./data:/home/openvscode-server:cached
    ports:
      - 3000:3000
    command: [
      "--host", "0.0.0.0",
      "--port", "3000",
      "--without-connection-token"
    ]
    restart: unless-stopped
```

For production, always use `--connection-token` or `--connection-token-file`:

```bash
docker run -it --init \
  -p 3000:3000 \
  -v "$(pwd)/workspace:/home/workspace:cached" \
  gitpod/openvscode-server:latest \
  --connection-token your-secret-token
```

### Accessing the IDE

Navigate to `http://your-server:3000/?tkn=your-secret-token` to connect. The token-based authentication is simpler than code-server's password approach but requires secure token management.

### Pros and Cons

| Pros | Cons |
|------|------|
| Tracks VS Code releases closely | Less documentation than code-server |
| Production-tested by Gitpod | Smaller community |
| Clean architecture | Fewer deployment tutorials available |
| No password hashing overhead | Token management can be cumbersome |

## Option 3: Eclipse Che — Kubernetes-Native Workspaces

**Eclipse Che** takes a fundamentally different approach. Instead of running a single IDE instance, it provisions entire development **workspaces** as Kubernetes pods. Each workspace can have its own stack of containers for the IDE frontend, build tools, databases, and more.

### Key Features

- Kubernetes-native workspace provisioning
- Devfile-based workspace configuration
- Multiple IDE frontends (VS Code, IntelliJ via JetBrains Gateway, custom)
- Team collaboration features
- Pre-configured development stacks for different languages
- Multi-tenant by design

### Kubernetes Deployment with Helm

```bash
# Install the Che Operator
kubectl create namespace eclipse-che
kubectl apply -f https://raw.githubusercontent.com/eclipse/che-operator/stable/deploy/operator.yaml

# Deploy Che
cat <<EOF | kubectl apply -f -
apiVersion: org.eclipse.che/v2
kind: CheCluster
metadata:
  name: eclipse-che
  namespace: eclipse-che
spec:
  components:
    cheServer:
      debug: false
      logLevel: INFO
    database:
      externalDB:
        container:
          image: postgres:16
    dashboard:
      logLevel: ERROR
  containerRegistry: {}
  networking:
    hostname: che.example.com
    tls:
      secretName: che-tls
EOF
```

### Devfile Configuration

A Devfile defines your development environment as code:

```yaml
schemaVersion: 2.2.0
metadata:
  name: python-django-workspace
components:
  - name: dev
    container:
      image: python:3.12
      memoryLimit: 2Gi
      cpuLimit: '2'
      mountSources: true
      endpoints:
        - name: django-dev
          exposure: public
          protocol: https
          targetPort: 8000
commands:
  - id: install
    exec:
      component: dev
      commandLine: pip install -r requirements.txt
      workingDir: ${PROJECT_SOURCE}
  - id: run
    exec:
      component: dev
      commandLine: python manage.py runserver 0.0.0.0:8000
      workingDir: ${PROJECT_SOURCE}
```

### Docker Compose (Lighter Setup)

For non-Kubernetes environments, Che's `chectl` can deploy a minimal instance:

```bash
chectl server:deploy \
  --platform minikube \
  --che-operator-cr-patch-yaml che-patch.yaml
```

### Pros and Cons

| Pros | Cons |
|------|------|
| Full Kubernetes-native architecture | Requires Kubernetes — significant infrastructure overhead |
| Devfile standard for reproducible environments | Steep learning curve |
| Multi-tenant with per-user workspaces | Heavy resource usage (Kubernetes + workspace containers) |
| Supports multiple IDE frontends | Overkill for solo developers |
| Team collaboration built in | Complex to maintain |

## Option 4: Theia — Cloud & Desktop IDE Platform

**Theia** (by the Eclipse Foundation) is a framework for building custom IDEs and tooling platforms. Unlike the other options, Theia is not a pre-packaged VS Code clone — it's a toolkit for building your own browser-based IDE with the features you need.

### Key Features

- Extensible framework for custom IDEs
- Supports VS Code extensions via compatibility layer
- Can run as desktop app (Electron) or in browser
- Multi-root workspace support
- Built-in terminal with multiple shell support
- Plugin system for deep customization

### Docker Deployment

```yaml
version: "3.8"
services:
  theia-ide:
    image: theiaide/theia:latest
    container_name: theia-ide
    user: "1000:1000"
    environment:
      - THEIA_CONFIG_DIR=/home/theia/.theia
    volumes:
      - ./workspace:/home/project
      - ./theia-config:/home/theia/.theia
    ports:
      - 3000:3000
    command: >
      /bin/sh -c "
        yarn theia start /home/project \
          --hostname=0.0.0.0 \
          --port=3000 \
          --ws=/theia \
          --auth=none
      "
    restart: unless-stopped
```

For a production setup with authentication, you'd build a custom Theia application:

```dockerfile
FROM node:20-bookworm-slim

RUN apt-get update && apt-get install -y \
    build-essential pkg-config python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /home/theia

# Create package.json for custom Theia app
RUN cat <<EOF > package.json
{
  "private": true,
  "theia": {
    "frontend": {
      "config": {
        "applicationName": "My Custom IDE",
        "warnOnPotentiallyInsecureHostPattern": false
      }
    }
  },
  "dependencies": {
    "@theia/core": "latest",
    "@theia/filesystem": "latest",
    "@theia/workspace": "latest",
    "@theia/terminal": "latest",
    "@theia/editor": "latest",
    "@theia/languages": "latest",
    "@theia/git": "latest",
    "@theia/markers": "latest",
    "@theia/outline-view": "latest",
    "@theia/preferences": "latest",
    "@theia/task": "latest",
    "@theia/navigator": "latest",
    "@theia/plugin-ext-vscode": "latest",
    "@theia/search-in-workspace": "latest",
    "@theia/scm": "latest",
    "@theia/scm-extra": "latest",
    "@theia/keymaps": "latest",
    "@theia/console": "latest",
    "@theia/messages": "latest",
    "@theia/plugin-ext": "latest",
    "@theia/vsx-registry": "latest",
    "@theia/mini-browser": "latest",
    "@theia/property-view": "latest",
    "@theia/timeline": "latest",
    "@theia/toolbar": "latest",
    "@theia/callhierarchy": "latest"
  },
  "devDependencies": {
    "@theia/cli": "latest"
  }
}
EOF

RUN yarn install --network-timeout 100000
RUN yarn theia build

EXPOSE 3000

ENTRYPOINT ["yarn", "theia", "start", "/home/project", "--hostname=0.0.0.0"]
```

### Building a Custom Theia App

```bash
# Install Yeoman and Theia generator
npm install -g yo generator-theia-extension

# Create a new Theia application
mkdir my-ide && cd my-ide
yo theia-extension

# Choose your extensions and build
yarn install
yarn build
yarn start
```

### Pros and Cons

| Pros | Cons |
|------|------|
| Fully customizable — build your own IDE | Requires development effort to configure |
| VS Code extension compatibility | Not a drop-in VS Code replacement |
| Can run as desktop or web app | Smaller extension ecosystem than native VS Code |
| Multi-root workspace support | Documentation scattered across Eclipse Foundation |
| Active open-source governance | Fewer ready-to-use deployment guides |

## Head-to-Head Comparison

| Feature | code-server | OpenVSCode Server | Eclipse Che | Theia |
|---------|-------------|-------------------|-------------|-------|
| **Based on** | VS Code | VS Code (Gitpod fork) | VS Code + JetBrains | Custom framework |
| **Deployment complexity** | Low | Low | High (Kubernetes) | Medium |
| **VS Code extensions** | ✅ Full support | ✅ Full support | ✅ Full support | ⚠️ Compatibility layer |
| **Multi-user** | ❌ Single-user | ❌ Single-user | ✅ Built-in | ⚠️ Custom required |
| **Terminal** | ✅ Integrated | ✅ Integrated | ✅ Per-workspace | ✅ Integrated |
| **Git integration** | ✅ Built-in | ✅ Built-in | ✅ Built-in | ✅ Built-in |
| **Docker support** | ✅ Native | ✅ Native | ✅ Via workspace containers | ✅ Via plugins |
| **Resource usage** | ~500MB RAM | ~500MB RAM | 2GB+ RAM (K8s overhead) | ~400MB RAM |
| **Best for** | Solo developers | Solo developers | Teams & enterprises | Custom IDE builders |
| **GitHub stars** | 67k+ | 4k+ | 8k+ | 5k+ |

## Which Should You Choose?

### Choose code-server if:
- You want the closest experience to desktop VS Code
- You're a solo developer or small team
- You need quick setup with minimal configuration
- You want the largest community and most tutorials

### Choose OpenVSCode Server if:
- You want upstream VS Code tracking with faster updates
- You prefer simpler token-based authentication
- You're already using Gitpod and want self-hosted parity
- You want a cleaner codebase to build on top of

### Choose Eclipse Che if:
- You're running Kubernetes and need multi-tenant workspaces
- You need per-developer isolated environments with custom stacks
- Your team uses different languages and needs pre-configured setups
- You want Devfile-based reproducible development environments

### Choose Theia if:
- You want to build a custom IDE with specific features
- You need deep integration with proprietary tools or workflows
- You want both desktop and web deployment from the same codebase
- You need multi-root workspace support with custom tooling

## Recommended Production Setup

For most self-hosters, **code-server behind Caddy** is the simplest production-ready configuration:

```docker-compose
version: "3.8"
services:
  code-server:
    image: lscr.io/linuxserver/code-server:latest
    environment:
      - PUID=1000
      - PGID=1000
      - PASSWORD=${CODE_SERVER_PASSWORD}
      - DEFAULT_WORKSPACE=/config/workspace
    volumes:
      - ./code-server-config:/config
      - ./workspace:/config/workspace
    networks:
      - ide-network
    restart: unless-stopped

  caddy:
    image: caddy:2
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy-data:/data
      - caddy-config:/config
    networks:
      - ide-network
    restart: unless-stopped

volumes:
  caddy-data:
  caddy-config:

networks:
  ide-network:
```

```caddyfile
# Caddyfile
ide.example.com {
    reverse_proxy code-server:8443
    tls your@email.com
}
```

Start everything with:

```bash
export CODE_SERVER_PASSWORD=$(openssl rand -base64 32)
docker compose up -d
echo "Your password: $CODE_SERVER_PASSWORD"
```

## Performance Tips

- **Use SSD storage**: IDE operations (file indexing, search, IntelliSense) are I/O-heavy. NVMe storage makes a noticeable difference.
- **Allocate sufficient RAM**: VS Code with extensions typically needs 1–2GB RAM for smooth operation.
- **Enable gzip compression**: If using a reverse proxy, enable compression to reduce bandwidth for large files.
- **Pre-install extensions**: Mount a pre-configured extensions directory to avoid downloading on first launch.
- **Use Docker volume caching**: On macOS with Docker Desktop, use `:cached` volume flags for better I/O performance.

## Security Considerations

Running a web IDE exposes a powerful development environment to the network. Follow these practices:

1. **Always use HTTPS** — Never expose an IDE over plain HTTP, even on a local network.
2. **Strong authentication** — Use long passwords or tokens. Enable two-factor authentication via your reverse proxy if possible.
3. **Network isolation** — Place the IDE behind a VPN (Tailscale, WireGuard) rather than exposing it directly to the internet.
4. **Keep images updated** — Regularly pull the latest Docker images for security patches.
5. **Limit extensions** — Only install extensions from trusted publishers. Malicious extensions can access your codebase and credentials.
6. **Regular backups** — Back up your workspace and configuration directories. A simple `rsync` or Restic job works well.

## Conclusion

The self-hosted web IDE landscape in 2026 offers something for every developer. **code-server** remains the best all-around choice for most users — it's mature, well-documented, and delivers a near-perfect VS Code experience through the browser. **OpenVSCode Server** is a strong alternative if you prefer Gitpod's maintenance approach and cleaner architecture. **Eclipse Che** shines for teams that need Kubernetes-native, multi-tenant development environments with standardized workspace definitions. **Theia** is the right pick when you need to build a custom IDE platform rather than use an off-the-shelf solution.

Regardless of which option you choose, running your own web IDE gives you full control over your development environment, keeps your code private, and lets you develop from any device with a browser.
