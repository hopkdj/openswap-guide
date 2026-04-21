---
title: "Windmill vs n8n: Best Self-Hosted Zapier & Retool Alternative 2026"
date: 2026-04-16
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to self-hosting Windmill — an open-source workflow automation and internal tool builder. Compare with n8n, Zapier, and Retool. Docker setup, scripts, and best practices."
---

If you are looking for a self-hosted alternative to Zapier, Make (formerly Integromat), or Retool, **Windmill** deserves serious attention. While [n8n](https://n8n.io/) gets most of the spotlight in the open-source automation space, Windmill takes a fundamentally different approach — one that treats developers as first-class users while still offering a visual workflow builder for non-technical team members.

Windmill combines workflow automation, internal tool building, and scheduled job execution into a single platform. It is written in Rust, supports Python, TypeScript, Go, Bash, SQL, and more, and ships with a powerful UI builder for creating dashboards and admin panels.

## Why Self-Host Your Workflow Automation?

Workflow automation platforms touch every sensitive system in your infrastructure — databases, APIs, authentication providers, payment processors, and internal services. Handing that access to a third-party SaaS means:

- **Data leaves your network.** Every webhook, API call, and transformation passes through the vendor's servers. For organizations handling personal data, financial records, or healthcare information, this creates compliance headaches under GDPR, HIPAA, and SOC 2.
- **Vendor lock-in is real.** Migrating hundreds of workflows from Zapier to another platform is painful. SaaS tools deliberately make exports difficult. With a self-hosted solution, your workflows live in your Git repository, version-controlled and portable.
- **Unpredictable pricing.** Zapier charges per task. Make charges per operation. Both scale linearly with your usage. A self-hosted platform runs on your own hardware with a fixed monthly cost regardless of how many workflows you run.
- **Rate limiting and quotas.** SaaS platforms throttle your API calls. Self-hosting removes those artificial ceilings — your only limit is your server capacity.
- **Custom integrations.** Need to connect to an internal API that is not on the public internet? A self-hosted platform running inside your network can reach it directly.

Windmill addresses all of these concerns while offering a developer experience that rivals — and in many cases exceeds — what commercial platforms provide.

## What Is Windmill?

Windmill is an open-source developer platform that lets you turn scripts into workflows and workflows into applications. Its core architecture consists of three layers:

| Layer | Purpose |
|-------|---------|
| **Scripts** | Individual units of work written in Python, TypeScript, Go, Bash, SQL, or other languages. Each script has typed inputs, outputs, and resource connections. |
| **Flows** | Directed acyclic graphs (DAGs) that chain scripts together with conditions, loops, branching, and error handling. Think of these as your Zapier "Zaps." |
| **Apps** | UI dashboards built with a drag-and-drop editor that can invoke scripts and flows, display results in tables, charts, and forms, and serve as internal tools. Think of these as your Retool apps. |

Unlike n8n, which uses a node-based visual editor where every step is a drag-and-drop component, Windmill is code-first. You write scripts in your preferred language, and the platform handles scheduling, parallel execution, retries, and monitoring automatically. The UI builder then lets you wrap those scripts in polished internal interfaces.

### Key Features

- **Multi-language support** — Python, TypeScript, Node.js, Go, Bash, SQL, PHP, R, and more
- **Git-native** — all scripts and flows are stored in Git repositories, enabling code review and CI/CD
- **Resource management** — securely store database connections, API keys, and OAuth tokens
- **Built-in scheduler** — cron-like scheduling without external tools
- **Real-time execution logs** — stream logs as workflows run, with step-by-step tracing
- **App builder** — drag-and-drop UI components (tables, forms, charts, buttons) connected to your scripts
- **RBAC and teams** — role-based access control with groups and permissions
- **Worker pools** — scale horizontally by adding worker nodes for specific script types
- **Enterprise SSO** — SAML, OIDC, and LDAP support in the Enterprise edition

## Installation: [docker](https://www.docker.com/) Compose Setup

The fastest way to get Windmill running is with Docker Compose. The official setup includes the Windmill server, a PostgreSQL database, and LSP (Language Server Protocol) servers for code intelligence.

Create a directory and a `docker-compose.yml` file:

```bash
mkdir windmill && cd windmill
```

```yaml
version: "3.9"
services:
  db:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_PASSWORD: windmill
      POSTGRES_DB: windmill
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  windmill_server:
    image: ghcr.io/windmill-labs/windmill:main
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgres://postgres:windmill@db:5432/windmill
      BASE_URL: http://localhost:8000
    volumes:
      - worker_logs:/tmp/windmill/logs

  windmill_worker:
    image: ghcr.io/windmill-labs/windmill:main
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgres://postgres:windmill@db:5432/windmill
      WORKER_GROUP: default
    command: ["start-worker", "--path", "/tmp/windmill/base"]
    volumes:
      - worker_tmp:/tmp/windmill

  windmill_worker_native:
    image: ghcr.io/windmill-labs/windmill:main
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgres://windmill:windmill@db:5432/windmill
      WORKER_GROUP: native
    command: ["start-worker", "--path", "/tmp/windmill/base", "--no-native-dir"]

  windmill_lsp:
    image: ghcr.io/windmill-labs/windmill-lsp:latest
    restart: unless-stopped
    ports:
      - "3001:3001"

volumes:
  pg_data:
  worker_tmp:
  worker_logs:
```

Start the stack:

```bash
docker compose up -d
```

Once running, open `http://localhost:8000` in your browser. The default credentials are:

- **Email:** `admin@windmill.dev`
- **Password:** `changeme`

Change the admin password immediately after your first login.

### Production Hardening

For a production deployment, you should:

```bash
# 1. Set a strong admin password at first boot
# Do this via the UI or set the env var before starting:
ADMIN_PASSWORD=your-secure-password-123!

# 2[caddy](https://caddyserver.com/) a reverse proxy with TLS
# Example with Caddy (place in Caddyfile):
# windmill.example.com {
#     reverse_proxy localhost:8000
# }

# 3. Pin the Docker image to a specific version tag
# Instead of :main, use :v1.534 or the latest release tag
# This prevents unexpected breaking changes on docker compose pull

# 4. Configure resource limits for workers
# Add to docker-compose.yml under each worker:
# deploy:
#   resources:
#     limits:
#       cpus: '2'
#       memory: 2G
```

## Writing Your First Script

Windmill scripts are plain code with typed inputs and outputs. Here is a practical example — a script that checks the health of multiple services and sends an alert if any are down:

```python
# health_check.py
from urllib.request import urlopen, Request
from datetime import datetime
import json

def main(
    services: list[str],
    timeout: int = 5
) -> dict:
    """Check health endpoints and report status."""
    results = []

    for url in services:
        try:
            req = Request(url, method="HEAD")
            resp = urlopen(req, timeout=timeout)
            status = resp.status
        except Exception as e:
            status = 0

        results.append({
            "url": url,
            "status": status,
            "ok": 200 <= status < 400,
            "checked_at": datetime.utcnow().isoformat()
        })

    down_services = [r["url"] for r in results if not r["ok"]]
    return {
        "total": len(results),
        "healthy": len(results) - len(down_services),
        "down": down_services,
        "details": results
    }
```

In Windmill, you save this as a script resource. The function signature defines the input schema — Windmill automatically generates a UI form with fields for `services` (a text array) and `timeout` (an integer with default 5).

Now wrap it in a flow that sends a notification when services are down:

```typescript
// send_alert.ts
import { sendSlackMessage } from "windmill";

export async function main(down_services: string[]) {
    if (down_services.length === 0) {
        return { sent: false, reason: "all services healthy" };
    }

    const message = `🚨 *Service Alert*\n\nThe following services are down:\n${
        down_services.map(s => `• ${s}`).join("\n")
    }\n\nChecked at: ${new Date().toISOString()}`;

    const slack = await sendSlackMessage({
        channel: "#infrastructure",
        text: message,
        token: "SLACK_BOT_TOKEN"
    });

    return { sent: true, response: slack };
}
```

In the flow editor, you connect the `health_check` script to the `send_alert` script with a conditional branch: if `down_services` is not empty, trigger the alert. The entire flow executes as a single DAG with automatic retry logic.

## Building an Internal Tool (App)

Windmill's app builder lets you create dashboards without writing frontend code. Here is how you build a service monitoring dashboard:

1. **Create a new App** from the Windmill dashboard.
2. **Add a Table component** — bind it to the output of your `health_check` flow. The table auto-generates columns from the script's return type.
3. **Add a Bar Chart** — visualize the ratio of healthy vs. down services over time.
4. **Add a Button** — label it "Run Health Check" and bind it to trigger the flow on click.
5. **Add a Date Picker** — let users select a time range to view historical results.

The app builder supports text inputs, dropdowns, file uploads, code editors, JSON viewers, and 20+ component types. Every component can be connected to script outputs, creating reactive dashboards that update in real time as workflows execute.

### Example: Database Admin Panel

```python
# db_query.py
import psycopg2

def main(
    query: str,
    db_resource: "postgresql"
) -> list[dict]:
    """Execute a read-only SQL query against a connected database."""
    conn = psycopg2.connect(
        host=db_resource["host"],
        port=db_resource["port"],
        dbname=db_resource["dbname"],
        user=db_resource["user"],
        password=db_resource["password"]
    )
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results
```

Bind this script to a Text Area component (for the query) and a Table component (for the results), and you have a functional database query interface in under five minutes. Add a Button to execute, a Dropdown to select databases, and a Status indicator for query duration.

## Windmill vs n8n vs Zapier: Detailed Comparison

| Feature | Windmill | n8n | Zapier | Retool |
|---------|----------|-----|--------|--------|
| **Primary paradigm** | Code-first workflows | Visual node editor | Visual recipe builder | Visual app builder |
| **Languages** | Python, TS, Go, Bash, SQL, PHP, R | JavaScript (Function nodes) | None (GUI only) | JavaScript (limited) |
| **Self-hosted** | Yes (AGPLv3 + Enterprise) | Yes (Sustainable Use License) | No | Partial (paid) |
| **Git integration** | Native (all code in Git) | Via version control plugin | No | Via Git sync (paid) |
| **UI builder** | Full drag-and-drop app builder | No (workflows only) | No | Full drag-and-drop app builder |
| **Scheduling** | Built-in cron scheduler | Built-in cron scheduler | Built-in (paid) | No |
| **Worker scaling** | Horizontal worker pools | Single instance + queue mode | N/A | N/A |
| **Pricing model** | Free open-source / Enterprise per seat | Free self-hosted / Cloud per workflow run | Per task (expensive at scale) | Per user (expensive) |
| **Integrations** | Any (write custom code) | 400+ pre-built nodes | 7,000+ pre-built apps | 50+ pre-built + custom |
| **Learning curve** | Moderate (requires coding) | Low to moderate | Low | Low to moderate |
| **Community** | Growing (12k+ GitHub stars) | Large (50k+ GitHub stars) | Massive | Large |
| **Audit log** | Full execution history with diffs | Execution log | Limited (paid) | Limited (paid) |
| **SSO / SAML** | Enterprise edition | Cloud + Enterprise | Paid plans | Paid plans |

## When to Choose Windmill

Windmill is the right choice when:

- **Your team includes developers** who prefer writing Python or TypeScript over configuring visual nodes.
- **You need both workflows and internal tools** from a single platform — the app builder is a significant advantage over n8n.
- **You run high-volume automations** where SaaS per-task pricing becomes prohibitive. Windmill's worker pools scale horizontally to handle thousands of concurrent executions.
- **You require Git-native version control** for compliance, code review, and rollback capabilities.
- **You need to connect to internal systems** that are not accessible from the public internet.

## When n8n Might Be Better

Consider n8n instead if:

- **Your team is non-technical** and needs a purely visual, drag-and-drop experience.
- **You rely heavily on pre-built integrations** — n8n has over 400 nodes with authentication handling built in.
- **You are already in the n8n ecosystem** and have hundreds of existing workflows.
- **You need webhook triggers** with a simpler setup — n8n's webhook nodes are more mature and battle-tested.

## Scaling Windmill in Production

Windmill's architecture separates the server (API, UI, scheduler) from workers (script execution). This means you can scale workers independently:

```yaml
# docker-compose.production.yml — add more workers as needed
  windmill_worker_python:
    image: ghcr.io/windmill-labs/windmill:main
    environment:
      DATABASE_URL: postgres://postgres:windmill@db:5432/windmill
      WORKER_GROUP: python
      NUM_WORKERS: 4
    command: ["start-worker", "--path", "/tmp/windmill/base", "--no-native-dir"]
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G

  windmill_worker_ts:
    image: ghcr.io/windmill-labs/windmill:main
    environment:
      DATABASE_URL: postgres://postgres:windmill@db:5432/windmill
      WORKER_GROUP: typescript
      NUM_WORKERS: 4
    command: ["start-worker", "--path", "/tmp/windmill/base", "--no-native-dir"]
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 4G
```

Each worker pool can be tuned for specific languages. Python workers get more memory for data processing, while TypeScript workers get more CPU for API orchestration. Tag your scripts with the appropriate worker group, and Windmill routes execution automatically.

For high availability, run multiple server instances behind a load balancer, all connected to the same PostgreSQL database. Use an external PostgreSQL cluster (managed or self-hosted with Patroni) for durability.

## Security Best Practices

- **Never hardcode secrets.** Use Windmill's built-in resource and variable store. Resources are encrypted at rest and scoped by workspace.
- **Enable audit logging.** Every script execution, configuration change, and login is recorded. Export logs to your SIEM for compliance.
- **Use workspace isolation.** Create separate workspaces for development, staging, and production. Each workspace has its own resources, scripts, and permissions.
- **Limit resource scopes.** A script that reads from a database should use a read-only database user, not an admin account.
- **Run workers in isolated containers.** For untrusted scripts (e.g., scripts from multiple teams), use the native worker isolation mode which runs each script in a fresh container.
- **Keep dependencies pinned.** Windmill automatically resolves and caches dependencies (pip, npm, go modules). Pin your versions in scripts to ensure reproducible builds.

## Conclusion

Windmill fills a unique position in the self-hosted automation landscape. It is not merely a Zapier replacement — it is closer to a combination of Zapier, Retool, and GitHub Actions in a single open-source package. The code-first approach may feel intimidating to non-developers, but the visual app builder and flow editor make it accessible enough for mixed teams.

If you are already using n8n and are happy with it, there is no urgent reason to switch. But if you find yourself writing custom code inside n8n's Function nodes, struggling with performance at scale, or wishing you had a built-in UI builder for internal tools, Windmill is worth evaluating.

The platform is actively developed, backed by a well-funded company (Windmill Labs), and the open-source edition is genuinely feature-rich — not a crippled free tier. For organizations that take data sovereignty seriously, it is one of the strongest self-hosted workflow automation options available in 2026.

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
