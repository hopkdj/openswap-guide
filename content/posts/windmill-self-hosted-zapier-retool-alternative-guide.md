---
title: "Windmill: Self-Hosted Zapier & Retool Alternative — Complete Guide 2026"
date: 2026-04-14
tags: ["comparison", "guide", "self-hosted", "automation", "developer-tools"]
draft: false
description: "Complete guide to Windmill, the open-source developer platform for workflows and internal tools. Docker deployment, scripting guide, and comparison with Zapier and Retool."
---

If you're running workflows with Zapier or building internal tools on Retool, you're paying per-execution and per-seat fees that compound fast as your team scales. **Windmill** is an open-source, self-hosted developer platform that replaces both — offering workflow automation *and* internal UI building from a single code-first platform.

In this guide, you'll learn what Windmill is, how it compares to Zapier and Retool, and exactly how to deploy and use it on your own infrastructure.

---

## Quick Comparison: Windmill vs Zapier vs Retool

| Feature | **Windmill** | **Zapier** | **Retool** |
|---|---|---|---|
| **License** | AGPLv3 (open-source) | Proprietary SaaS | Proprietary (self-hosted paid) |
| **Pricing (self-hosted)** | Free (Community Edition) | N/A | $10–$50/seat/month |
| **Workflow Engine** | ✅ Native (flows, schedules) | ✅ Native | ❌ (needs external tool) |
| **Internal UI Builder** | ✅ Native (frontend components) | ❌ | ✅ Native |
| **Language Support** | Python, TypeScript, Go, SQL, Bash, Shell | No-code only | JavaScript |
| **Code-First** | ✅ Scripts are version-controlled code | ❌ | ⚠️ JS snippets |
| **Git Integration** | ✅ Full (push/pull, branches) | ❌ | ⚠️ Limited |
| **Self-Hosted** | ✅ Docker / Kubernetes | ❌ | ✅ (Enterprise only) |
| **AI Code Generation** | ✅ Built-in AI script generation | ✅ (AI Zap creation) | ✅ (AI component gen) |
| **Min RAM** | 2 GB | N/A | 4 GB |
| **Best For** | Dev teams, SREs, data engineers | Non-technical users, marketing ops | Internal tools, admin panels |

---

## Why Self-Host Your Automation Platform?

Running Zapier or Retool as a SaaS is convenient, but it comes with real trade-offs:

### Cost at Scale

Zapier charges per task. A moderate workflow that processes 1,000 records and triggers 5 actions each time burns through 5,000 tasks per run. At $50/month for 50,000 tasks, you can exhaust a plan in a single week of batch processing. Retool charges per seat — every developer, analyst, and support agent who needs access adds $5–$50/month to your bill.

Windmill's Community Edition is free and self-hosted. You only pay for the infrastructure it runs on.

### Data Privacy and Compliance

When your workflows process customer data, financial records, or health information, sending that data through third-party SaaS pipelines creates compliance overhead. Self-hosting keeps everything within your network boundary — no data leaves your servers, no vendor audit trail to manage, no SOC 2 questionnaires to fill out.

### Code Ownership and Version Control

Zapier workflows live inside Zapier. Retool apps live inside Retool. Windmill scripts and flows live in Git. Every change is tracked, every version is restorable, and your automation logic is part of your codebase — not trapped in a SaaS platform's proprietary format.

### No Vendor Lock-In

Windmill scripts are plain Python, TypeScript, Go, or SQL. If you ever decide to stop using the platform, your scripts run anywhere. There's no proprietary node format or visual editor dependency to decode.

---

## What Is Windmill?

**Windmill** is an open-source developer platform that combines three capabilities into a single system:

1. **Script Execution** — Write scripts in Python, TypeScript, Go, SQL, Bash, or Shell and run them on a schedule, on a webhook trigger, or on demand.

2. **Workflow Orchestration** — Chain scripts together into flows with branching logic, loops, error handling, and parallel execution. Think of it as a code-first Airflow or Temporal.

3. **Internal App Building** — Generate user interfaces from scripts automatically, or build custom UIs with Windmill's frontend components (tables, forms, charts, buttons). Think of it as a code-first Retool.

The platform was created by Ruben Fiszel (formerly at Airflow) and is backed by Windmill Labs. It's used by companies like Coinbase, Ramp, and Brex for internal tooling and automation.

### Key Features

- **Multi-language support** — Python, TypeScript, Go, SQL, Bash, Shell, and PHP scripts
- **Native Git sync** — scripts stored in Git repositories with push/pull and branch support
- **Built-in scheduler** — cron-like scheduling with timezone support and concurrency controls
- **Webhook triggers** — expose any script as an HTTP endpoint
- **Resource management** — centrally manage database connections, API keys, and OAuth tokens
- **Flow engine** — DAG-based workflow execution with retries, timeouts, and error branches
- **App builder** — auto-generate UIs from scripts or build custom interfaces
- **Execution queues** — isolate workloads across different worker pools
- **Audit logging** — full execution history with inputs, outputs, and duration
- **Role-based access control** — fine-grained permissions for users and groups

---

## Installing Windmill with Docker Compose

The fastest way to get Windmill running is with the official Docker Compose setup. This deploys Windmill with PostgreSQL and a single worker process.

### Prerequisites

- Docker and Docker Compose installed
- At least 2 GB RAM available
- A domain name (optional, for HTTPS)

### Step 1: Create the Compose File

Create a directory for Windmill and write the compose configuration:

```bash
mkdir -p ~/windmill && cd ~/windmill
```

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:16
    container_name: windmill-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: windmill
      POSTGRES_USER: windmill
      POSTGRES_PASSWORD: ${DB_PASSWORD:-changeme_usesomethingstrong}
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U windmill"]
      interval: 10s
      timeout: 5s
      retries: 5

  windmill-server:
    image: ghcr.io/windmill-labs/windmill:latest
    container_name: windmill-server
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgres://windmill:${DB_PASSWORD:-changeme_usesomethingstrong}@postgres:5432/windmill
      BASE_URL: http://localhost:8000
      MODE: server
    depends_on:
      postgres:
        condition: service_healthy

  windmill-worker:
    image: ghcr.io/windmill-labs/windmill:latest
    container_name: windmill-worker
    restart: unless-stopped
    environment:
      DATABASE_URL: postgres://windmill:${DB_PASSWORD:-changeme_usesomethingstrong}@postgres:5432/windmill
      MODE: worker
      WORKER_GROUP: default
      NUM_WORKERS: 8
      PATH_DATA: /tmp/windmill/data
      SLEEP_QUEUE: 0.1
    depends_on:
      postgres:
        condition: service_healthy

  windmill-worker-native:
    image: ghcr.io/windmill-labs/windmill:latest
    container_name: windmill-worker-native
    restart: unless-stopped
    environment:
      DATABASE_URL: postgres://windmill:${DB_PASSWORD:-changeme_usesomethingstrong}@postgres:5432/windmill
      MODE: worker
      WORKER_GROUP: native
      NUM_WORKERS: 4
      SLEEP_QUEUE: 0.1
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  pg_data:
```

Save this as `docker-compose.yml`.

### Step 2: Start the Stack

```bash
docker compose up -d
```

Wait about 30 seconds for the database to initialize, then open `http://localhost:8000` in your browser. The default credentials are:

- **Username:** `admin`
- **Password:** `changeme`

Change these immediately in the admin panel.

### Step 3: Verify the Installation

```bash
docker compose ps
```

You should see four containers running: `postgres`, `windmill-server`, `windmill-worker`, and `windmill-worker-native`.

---

## Production Deployment with Reverse Proxy

For a production setup, add a reverse proxy and HTTPS termination. Here's a Caddy configuration that handles TLS automatically:

### Docker Compose (Production)

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:16
    container_name: windmill-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: windmill
      POSTGRES_USER: windmill
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./postgres-init:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U windmill"]
      interval: 10s
      timeout: 5s
      retries: 5

  windmill-server:
    image: ghcr.io/windmill-labs/windmill:latest
    container_name: windmill-server
    restart: unless-stopped
    environment:
      DATABASE_URL: postgres://windmill:${DB_PASSWORD}@postgres:5432/windmill
      BASE_URL: https://windmill.yourdomain.com
      MODE: server
    depends_on:
      postgres:
        condition: service_healthy

  windmill-worker:
    image: ghcr.io/windmill-labs/windmill:latest
    container_name: windmill-worker
    restart: unless-stopped
    environment:
      DATABASE_URL: postgres://windmill:${DB_PASSWORD}@postgres:5432/windmill
      MODE: worker
      WORKER_GROUP: default
      NUM_WORKERS: 16
      SLEEP_QUEUE: 0.1
    depends_on:
      postgres:
        condition: service_healthy

  caddy:
    image: caddy:2
    container_name: windmill-caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - windmill-server

volumes:
  pg_data:
  caddy_data:
  caddy_config:
```

### Caddyfile

```
windmill.yourdomain.com {
    reverse_proxy windmill-server:8000
}
```

This gives you automatic HTTPS with Let's Encrypt. No certificate management needed.

---

## Writing Your First Script

Windmill scripts are plain code files. Let's create a Python script that queries a database and sends a report.

### Step 1: Create a Script

From the Windmill UI, click **Scripts** → **+ Script** → **Python**. Or use the CLI if you have Git sync configured.

```python
# /script/report_daily_metrics.py
from datetime import datetime, timedelta
import json

def main(
    db_host: str,
    db_port: int = 5432,
    db_name: str = "production",
    report_date: str = "today",
    slack_webhook: str = ""
) -> dict:
    """Generate a daily metrics report and optionally post to Slack."""
    
    # Parse date
    if report_date == "today":
        target = datetime.utcnow().date()
    else:
        target = datetime.strptime(report_date, "%Y-%m-%d").date()
    
    # Simulated query results (replace with actual DB query)
    metrics = {
        "date": str(target),
        "total_users": 12_847,
        "active_users": 3_291,
        "new_signups": 142,
        "revenue": 89_340.50,
        "support_tickets_open": 23,
    }
    
    # Calculate changes
    metrics["activity_rate"] = round(
        metrics["active_users"] / metrics["total_users"] * 100, 2
    )
    
    # Post to Slack if webhook provided
    if slack_webhook:
        import urllib.request
        
        message = (
            f"📊 *Daily Report — {metrics['date']}*\n"
            f"• Active Users: {metrics['active_users']} "
            f"({metrics['activity_rate']}%)\n"
            f"• New Signups: {metrics['new_signups']}\n"
            f"• Revenue: ${metrics['revenue']:,.2f}\n"
            f"• Open Tickets: {metrics['support_tickets_open']}"
        )
        
        payload = json.dumps({
            "text": "Daily Metrics Report",
            "blocks": [{
                "type": "section",
                "text": {"type": "mrkdwn", "text": message}
            }]
        }).encode()
        
        req = urllib.request.Request(
            slack_webhook,
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req)
    
    return metrics
```

### Step 2: Set Up Database Resources

Instead of hardcoding credentials, use Windmill's resource system:

1. Go to **Resources** → **+ Resource** → **PostgreSQL**
2. Fill in your connection details (host, port, database, user, password)
3. Name it `production_db`
4. Windmill stores the credentials encrypted and injects them at runtime

Now modify the script to use the resource:

```python
from datetime import datetime

def main(production_db: dict, report_date: str = "today") -> dict:
    """Query production database for daily metrics."""
    import psycopg2
    
    conn = psycopg2.connect(
        host=production_db["host"],
        port=production_db["port"],
        dbname=production_db["dbname"],
        user=production_db["user"],
        password=production_db["password"],
    )
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE created_at::date = %s) as new_signups,
            COUNT(*) FILTER (WHERE last_seen::date = %s) as active_today,
            COUNT(*) as total_users
        FROM users
    """, (report_date, report_date))
    
    row = cursor.fetchone()
    conn.close()
    
    return {
        "new_signups": row[0],
        "active_today": row[1],
        "total_users": row[2],
        "activity_rate": round(row[1] / row[2] * 100, 2) if row[2] else 0,
    }
```

Windmill automatically passes the resource as a typed argument — no environment variables or secret management needed.

---

## Building a Workflow (Flow)

Scripts become powerful when chained together. Windmill's flow engine lets you connect scripts into DAGs with branching, loops, and error handling.

Here's a real-world example: a data pipeline that extracts data, transforms it, loads it into a warehouse, and sends a notification.

### Flow Definition (JSON/YAML via UI)

```json
{
  "summary": "ETL Pipeline — Extract, Transform, Load, Notify",
  "description": "Daily data pipeline that pulls data from production, transforms it, loads into analytics warehouse, and posts results to Slack.",
  "schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "extract_date": { "type": "string", "format": "date" }
    }
  },
  "value": {
    "modules": [],
    "failure_module": {
      "value": { "id": "notify_failure", "path": "slack/notify_error", "input": { "error": "flow_failure_error" } }
    },
    "nodes": [
      {
        "id": "extract",
        "path": "scripts/extract_from_production",
        "input": { "extract_date": "extract_date" }
      },
      {
        "id": "transform",
        "path": "scripts/transform_data",
        "input": { "raw_data": "extract.result" }
      },
      {
        "id": "load",
        "branch": {
          "if": { "expr": "transform.result.row_count > 0" },
          "then": {
            "id": "load_warehouse",
            "path": "scripts/load_to_warehouse",
            "input": { "data": "transform.result" }
          },
          "else": {
            "id": "skip_load",
            "value": { "type": "identity", "input": { "value": "No data to load" } }
          }
        }
      },
      {
        "id": "notify_success",
        "path": "slack/notify_success",
        "input": {
          "summary": "ETL completed",
          "rows_processed": "transform.result.row_count"
        }
      }
    ]
  }
}
```

### What This Flow Does

1. **Extract** — Runs a Python script to pull data from the production database
2. **Transform** — Cleans, validates, and reshapes the data
3. **Conditional Load** — Only loads to the warehouse if there's data to process
4. **Notify** — Sends a Slack message with the results
5. **Failure Handler** — If anything fails, posts an error alert instead

You can add retry policies, timeouts, and parallel branches. The flow editor shows real-time execution status with color-coded node states.

---

## Building an Internal App

Windmill can auto-generate a UI from any script. For more control, build custom interfaces with frontend components.

### Auto-Generated UI

Every script automatically gets a web form based on its type hints. The `report_daily_metrics` script above generates a form with:

- A date picker (string type)
- A number input for `db_port` (int type with default)
- Text fields for `db_host`, `db_name`, and `slack_webhook`
- A **Run** button that executes the script and displays the JSON result

No UI code needed.

### Custom App Builder

For a dashboard, use Windmill's app builder to combine multiple scripts and data sources:

```typescript
// /frontend/dashboard.tsx
// This is written as a Windmill frontend component

import { Box, Card, Text, Grid } from "@mantine/core";
import { LineChart } from "@mantine/charts";
import { useQuery } from "@windmill/react-client";

export default function Dashboard() {
  // Query a script that returns metrics
  const { data: metrics } = useQuery("scripts/get_daily_metrics", {
    refetchInterval: 300000, // 5 minutes
  });

  return (
    <Box p="xl">
      <Text size="xl" fw={700} mb="lg">
        Operations Dashboard
      </Text>

      <Grid>
        <Grid.Col span={4}>
          <Card shadow="sm" p="lg">
            <Text size="sm" c="dimmed">Active Users</Text>
            <Text size="xl" fw={700}>{metrics?.active_users ?? "—"}</Text>
          </Card>
        </Grid.Col>

        <Grid.Col span={4}>
          <Card shadow="sm" p="lg">
            <Text size="sm" c="dimmed">Revenue Today</Text>
            <Text size="xl" fw={700}>${metrics?.revenue?.toLocaleString() ?? "—"}</Text>
          </Card>
        </Grid.Col>

        <Grid.Col span={4}>
          <Card shadow="sm" p="lg">
            <Text size="sm" c="dimmed">Open Tickets</Text>
            <Text size="xl" fw={700}>{metrics?.support_tickets_open ?? "—"}</Text>
          </Card>
        </Grid.Col>
      </Grid>

      <LineChart
        data={metrics?.timeseries ?? []}
        dataKey="date"
        series={[
          { name: "users", color: "blue" },
          { name: "signups", color: "green" },
        ]}
        mt="xl"
      />
    </Box>
  );
}
```

Windmill handles the rendering, data fetching, and component styling. You write the logic, the platform handles the UI plumbing.

---

## Scaling Workers for Production

The default setup uses a single worker container. For production workloads, scale horizontally:

### Multiple Worker Groups

```yaml
  # CPU-intensive workers (data processing, image manipulation)
  windmill-worker-heavy:
    image: ghcr.io/windmill-labs/windmill:latest
    container_name: windmill-worker-heavy
    restart: unless-stopped
    environment:
      DATABASE_URL: postgres://windmill:${DB_PASSWORD}@postgres:5432/windmill
      MODE: worker
      WORKER_GROUP: heavy
      NUM_WORKERS: 4
      WORKER_CONCURRENCY: 2
    deploy:
      resources:
        limits:
          cpus: "4.0"
          memory: 4G

  # Lightweight workers (webhooks, notifications, API calls)
  windmill-worker-light:
    image: ghcr.io/windmill-labs/windmill:latest
    container_name: windmill-worker-light
    restart: unless-stopped
    environment:
      DATABASE_URL: postgres://windmill:${DB_PASSWORD}@postgres:5432/windmill
      MODE: worker
      WORKER_GROUP: light
      NUM_WORKERS: 32
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 2G
```

Assign scripts to specific worker groups by setting the `worker_group` field in the script configuration. Heavy scripts run on isolated workers so they don't block fast API calls.

### Kubernetes Deployment

Windmill also supports Helm charts for Kubernetes:

```bash
helm repo add windmill https://windmill-labs.github.io/helm-charts
helm repo update

helm install windmill windmill/windmill \
  --namespace windmill --create-namespace \
  --set postgresql.enabled=true \
  --set worker.replicas=6 \
  --set server.replicas=2 \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=windmill.yourdomain.com
```

This deploys with auto-scaling, health checks, and ingress routing out of the box.

---

## Git Sync and Version Control

Windmill's Git integration turns the platform into a proper development environment:

### Enable Git Sync

1. Go to **Settings** → **Git Sync**
2. Connect a Git repository (GitHub, GitLab, Gitea, etc.)
3. Set the sync direction (pull, push, or bidirectional)
4. Choose a branch (e.g., `main` for production, `dev` for staging)

### Workflow

```
# Developer workflow with Windmill + Git

# 1. Pull latest scripts from Git
windmill pull   # or via UI: Settings → Git Sync → Pull

# 2. Edit scripts locally in your IDE
vim scripts/extract_from_production.py
git add scripts/extract_from_production.py
git commit -m "Add pagination to extract script"
git push

# 3. Push to Windmill
windmill push   # or via UI: Settings → Git Sync → Push

# 4. Test in staging workspace, promote to production
```

Every script is a regular file in your repository. Windmill reads the file path as the script path, parses the function signature for arguments, and uses the file content as the script body. This means:

- **Code review** works through normal pull requests
- **CI/CD** can lint and test scripts before they reach Windmill
- **Rollback** is a `git revert` away
- **Local development** works in VS Code, Neovim, or any editor

---

## Monitoring and Observability

Windmill provides built-in monitoring for all executions:

### Execution Dashboard

The UI shows:
- Running scripts and flows with real-time status
- Execution history with duration, inputs, and outputs
- Failed executions with full error traces
- Schedule status and next run times

### API Monitoring

Windmill exposes metrics at `/api/admin/metrics` in Prometheus format:

```bash
curl http://localhost:8000/api/admin/metrics
```

Key metrics include:
- `windmill_script_executions_total` — total script runs
- `windmill_script_execution_duration_seconds` — execution time histogram
- `windmill_queue_depth` — pending jobs per worker group
- `windmill_worker_count` — active workers

### Log Aggregation

Send Windmill logs to your existing log stack:

```yaml
  windmill-server:
    # ... existing config ...
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"
    labels:
      logging: "promtail"
```

Then configure Promtail or Fluent Bit to scrape the container logs and ship them to Loki, Elasticsearch, or your preferred log backend.

---

## When Windmill Is the Right Choice

### ✅ Use Windmill when:

- You have a technical team comfortable with Python, TypeScript, or Go
- You need both workflow automation *and* internal tools in one platform
- You want Git-based version control for all your automation logic
- You're running scripts on a schedule or responding to webhooks
- You want to replace Zapier, Retool, or Airplane with a single self-hosted system
- You need fine-grained access control and audit logging

### ⚠️ Consider alternatives when:

- Your team is entirely non-technical — Zapier or n8n's visual editor may be easier
- You need heavy IoT / MQTT integration — Node-RED is purpose-built for that
- You want a managed service with zero ops — Windmill is self-hosted only
- You need complex data pipeline orchestration with backfill — Apache Airflow is more mature for that specific use case

---

## Summary

Windmill consolidates three platforms — workflow automation, internal tools, and script execution — into a single open-source system you can run on your own infrastructure. The code-first approach means your automation logic lives in Git, your scripts are portable, and there's no vendor lock-in.

For teams that are comfortable writing code and want to move away from per-execution SaaS pricing, Windmill is one of the most capable self-hosted automation platforms available in 2026. The combination of multi-language scripting, a DAG-based flow engine, auto-generated UIs, and full Git integration makes it a compelling foundation for any self-hosted automation stack.

Get started with the Docker Compose setup above, connect your database as a resource, and have your first script running within 10 minutes.
