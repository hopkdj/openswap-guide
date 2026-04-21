---
title: "Shuffle SOAR vs StackStorm vs IRIS: Self-Hosted Security Automation & Incident Response Guide 2026"
date: 2026-04-20
tags: ["comparison", "guide", "self-hosted", "security", "soar", "incident-response", "automation"]
draft: false
description: "Compare Shuffle SOAR, StackStorm, and IRIS — three powerful open-source platforms for self-hosted security automation, incident response, and event-driven orchestration in 2026."
---

When a security alert fires at 3 AM, your team needs more than just a notification — it needs action. Security Orchestration, Automation, and Response (SOAR) platforms bridge the gap between alert detection and incident resolution. They connect your existing tools, automate repetitive tasks, and give analysts a single workspace to manage investigations.

The commercial SOAR market is dominated by expensive enterprise platforms like Palo Alto Cortex XSOAR and Splunk SOAR, which carry hefty licensing costs and often require dedicated consultants to deploy. The open-source alternative is compelling: self-hosted platforms that keep your data on-premises, avoid vendor lock-in, and integrate with your existing security stack.

In this guide, we compare three of the most capable open-source platforms for security automation and incident response: **Shuffle SOAR**, **StackStorm**, and **IRIS**. Each takes a different approach, and understanding their strengths helps you pick the right tool for your security operations center (SOC) or DevOps team.

## Why Self-Host Your Security Automation Platform?

Running your own SOAR platform offers several advantages over cloud-based alternatives:

- **Data sovereignty**: Incident data, playbooks, and sensitive indicators of compromise (IOCs) never leave your infrastructure
- **Deep integration**: Self-hosted platforms connect directly to internal tools, SIEMs, and network devices without NAT or firewall complications
- **Cost control**: Open-source SOAR platforms eliminate per-seat licensing fees that can reach six figures annually for enterprise products
- **Customization**: Full access to source code means you can modify workflows, add integrations, and adapt the platform to your unique processes
- **Offline capability**: Security operations continue during internet outages or when external SaaS providers experience downtime

For teams already running self-hosted SIEMs like [Wazuh or Security Onion](../self-hosted-siem-wazuh-security-onion-elastic-guide/) or threat intelligence platforms like [MISP and OpenCTI](../misp-vs-opencti-vs-intelowl-self-hosted-threat-intelligence-guide-2026/), a self-hosted automation platform completes the stack.

## Project Overview

| Feature | Shuffle SOAR | StackStorm | IRIS |
|---------|-------------|------------|------|
| **Primary Focus** | Security automation (SOAR) | Event-driven IT automation | Incident response case management |
| **GitHub Stars** | 2,243 | 6,446 | 1,471 |
| **Language** | JavaScript | Python | Python |
| **License** | AGPL-3.0 | Apache-2.0 | LGPL-3.0 |
| **Last Updated** | April 2026 | February 2026 | April 2026 |
| **[docker](https://www.docker.com/) Support** | Native docker-compose | st2-docker repo | Native docker-compose |
| **Web UI** | Built-in workflow editor | Web UI (st2web) | Built-in case management UI |
| **Workflow Builder** | Visual drag-and-drop | YAML-based workflows | Timeline and case workflows |
| **Integrations** | 300+ native apps | 160 packs (6,000+ actions) | DFIR-focused analyzers |
| **MITRE ATT&CK** | Native mapping | Community packs | Native framework support |
| **ChatOps** | Bu[mattermost](https://mattermost.com/)xcellent (Slack, Mattermost, Teams) | Via webhooks |
| **API** | REST API | REST + CLI | REST API |
| **Best For** | Security teams wanting visual automation | DevOps/SRE teams needing event-driven ops | DFIR teams needing case management |

Shuffle SOAR positions itself as a general-purpose security automation platform with a visual workflow builder that lets analysts create playbooks without writing code. Its 300+ integrations cover everything from ticketing systems to threat intelligence feeds, and its MITRE ATT&CK framework mapping helps teams align automation with adversary tactics.

StackStorm, the veteran of the three (created in 2014), calls itself "IFTTT for Ops." Its strength lies in event-driven automation: when a monitoring alert fires, StackStorm can automatically run a remediation workflow, post to Slack, and update a ticket — all without human intervention. Its 160 integration packs cover infrastructure tools, cloud providers, and security products extensively.

IRIS takes a different angle entirely. Rather than focusing on workflow automation, IRIS is a collaborative incident response investigation platform. It excels at case management, evidence tracking, timeline reconstruction, and analyst collaboration during active investigations. Think of it as the case file system that sits alongside your automation tools.

## Shuffle SOAR: Visual Security Automation

Shuffle SOAR's standout feature is its drag-and-drop workflow editor. Security analysts who aren't developers can build com[plex](https://www.plex.tv/) playbooks by connecting nodes: trigger (a new alert), action (enrich with threat intel), decision (if score > threshold), and response (block IP, create ticket).

### Key Features

- **Visual workflow builder**: Node-based interface for creating automated playbooks
- **App ecosystem**: 300+ pre-built integrations with security tools, APIs, and services
- **OpenAPI import**: Import any OpenAPI specification to instantly create a new integration
- **Multi-tenancy**: Separate organizations, users, and workflows for different teams
- **Sub-workflows**: Reusable workflow components that can be called from other workflows
- **MITRE ATT&CK integration**: Tag workflows with tactics and techniques for compliance reporting
- **Webhook triggers**: Any tool that can send HTTP POST requests can trigger a Shuffle workflow

### Installation with Docker Compose

Shuffle provides the most straightforward deployment of the three platforms. A single `docker-compose.yml` file brings up the complete stack:

```yaml
# docker-compose.yml for Shuffle SOAR
services:
  frontend:
    image: ghcr.io/shuffle/shuffle-frontend:latest
    container_name: shuffle-frontend
    hostname: shuffle-frontend
    ports:
      - "3001:80"
      - "3443:443"
    networks:
      - shuffle
    environment:
      - BACKEND_HOSTNAME=shuffle-backend
    restart: unless-stopped
    depends_on:
      - backend

  backend:
    image: ghcr.io/shuffle/shuffle-backend:latest
    container_name: shuffle-backend
    hostname: shuffle-backend
    ports:
      - "5001:5001"
    networks:
      - shuffle
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /shuffle-apps:/shuffle-apps:z
      - /shuffle-files:/shuffle-files:z
    env_file: .env
    restart: unless-stopped

  orborus:
    image: ghcr.io/shuffle/orborus:latest
    container_name: shuffle-orborus
    hostname: shuffle-orborus
    networks:
      - shuffle
    environment:
      - SHUFFLE_BASE_URL=http://shuffle-backend:5001
      - SHUFFLE_SWARM_CONFIG=run
      - ENVIRONMENT=Shuffle
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    restart: unless-stopped

networks:
  shuffle:
    driver: bridge
```

Create a `.env` file alongside it:

```bash
# .env for Shuffle SOAR
BACKEND_HOSTNAME=shuffle-backend
FRONTEND_PORT=3001
FRONTEND_PORT_HTTPS=3443
BACKEND_PORT=5001
SHUFFLE_APP_HOTLOAD_LOCATION=./shuffle-apps
SHUFFLE_FILE_LOCATION=./shuffle-files
```

Start with:

```bash
docker compose up -d
```

The frontend will be available at `http://localhost:3001`. The default admin credentials are `admin@shuffler.io` / `shuffler`.

### Sample Workflow: Automated Phishing Response

A common use case is automating the initial triage of phishing reports. A Shuffle workflow might:

1. **Trigger**: Receive email via webhook from your mail server
2. **Action 1**: Extract URLs and attachments from the email
3. **Action 2**: Submit URLs to VirusTotal for reputation check
4. **Action 3**: Check sender IP against your threat intelligence platform
5. **Decision**: If malicious score > 70, quarantine the email and block the sender
6. **Action 4**: Create an incident ticket in your case management system
7. **Action 5**: Send notification to the security team channel

This entire workflow takes minutes to build in Shuffle's visual editor and runs automatically for every incoming phishing report.

## StackStorm: Event-Driven IT and Security Automation

StackStorm has been the backbone of event-driven automation for over a decade. Its architecture is built around a simple but powerful concept: when an event occurs, match it against rules, and if a rule fires, execute an action or workflow.

### Key Features

- **Event-driven architecture**: Every incoming event is evaluated against registered rules in real-time
- **Rules engine**: Pattern matching on event attributes with complex conditions
- **Action packs**: 160+ community-maintained packs with 6,000+ pre-built actions
- **Workflow engine**: YAML-based Orquesta workflows for multi-step automation
- **ChatOps**: Native integration with Slack, Mattermost, and Microsoft Teams
- **RBAC**: Fine-grained role-based access control for enterprise deployments
- **CLI**: Full-featured command-line interface for managing and triggering actions
- **Sensor framework**: Continuous monitoring of external systems for state changes

### Architecture

StackStorm's microservices architecture runs as multiple Docker containers:

- **st2api**: REST API and action execution engine
- **st2auth**: Authentication and authorization
- **st2stream**: Server-sent events for real-time updates
- **st2workflowengine**: Workflow orchestration
- **st2sensorcontainer**: Sensor and trigger management
- **st2actionrunner**: Action execution workers
- **MongoDB**: Event and execution storage
- **RabbitMQ**: Internal message bus
- **Redis**: Caching and coordination
- **PostgreSQL**: Rule evaluation metadata

### Installation with Docker Compose

StackStorm's official deployment uses the separate `st2-docker` repository. Here is the core composition:

```yaml
# docker-compose.yml for StackStorm (from StackStorm/st2-docker)
version: '3'

services:
  st2web:
    image: stackstorm/st2web:latest
    restart: on-failure
    environment:
      ST2_AUTH_URL: http://st2auth:9100/
      ST2_API_URL: http://st2api:9101/
      ST2_STREAM_URL: http://st2stream:9102/
    depends_on:
      - st2auth
      - st2api
      - st2stream
    ports:
      - "80:80"
    networks:
      - st2

  st2api:
    image: stackstorm/st2api:latest
    restart: on-failure
    environment:
      ST2_CONF_PATH: /etc/st2/st2.conf
    depends_on:
      - mongodb
      - rabbitmq
    volumes:
      - ./st2.conf:/etc/st2/st2.conf:ro
    networks:
      - st2

  st2auth:
    image: stackstorm/st2auth:latest
    restart: on-failure
    environment:
      ST2_CONF_PATH: /etc/st2/st2.conf
    depends_on:
      - mongodb
    volumes:
      - ./st2.conf:/etc/st2/st2.conf:ro
    networks:
      - st2

  st2stream:
    image: stackstorm/st2stream:latest
    restart: on-failure
    environment:
      ST2_CONF_PATH: /etc/st2/st2.conf
    depends_on:
      - mongodb
      - rabbitmq
    volumes:
      - ./st2.conf:/etc/st2/st2.conf:ro
    networks:
      - st2

  st2workflowengine:
    image: stackstorm/st2workflowengine:latest
    restart: on-failure
    environment:
      ST2_CONF_PATH: /etc/st2/st2.conf
    depends_on:
      - mongodb
      - rabbitmq
    volumes:
      - ./st2.conf:/etc/st2/st2.conf:ro
    networks:
      - st2

  mongodb:
    image: mongo:6
    restart: on-failure
    volumes:
      - mongodb_data:/data/db
    networks:
      - st2

  rabbitmq:
    image: rabbitmq:3-management
    restart: on-failure
    environment:
      RABBITMQ_DEFAULT_USER: st2admin
      RABBITMQ_DEFAULT_PASS: changeme123
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    networks:
      - st2

  redis:
    image: redis:7-alpine
    restart: on-failure
    networks:
      - st2

  postgres:
    image: postgres:15
    restart: on-failure
    environment:
      POSTGRES_PASSWORD: changeme123
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - st2

volumes:
  mongodb_data:
  rabbitmq_data:
  postgres_data:

networks:
  st2:
    driver: bridge
```

Install from the official repository:

```bash
git clone https://github.com/StackStorm/st2-docker.git
cd st2-docker
# Edit st2.conf with your configuration
docker compose up -d
```

### Sample Rule: Auto-Remediate Failed SSH Logins

```yaml
# rules/ssh_brute_force_remediation.yaml
---
name: "ssh_brute_force_remediation"
pack: "security"
description: "Block IP after 10 failed SSH login attempts within 5 minutes"
enabled: true

trigger:
  type: "core.st2.generic.trigger"
  parameters:
    trigger: "linux.log_event"
    pattern: "Failed password.*ssh"

criteria:
  trigger.count:
    type: "threshold"
    pattern: 10
    threshold:
      period: 300  # 5 minutes

action:
  ref: "linux.run_cmd"
  parameters:
    cmd: "iptables -A INPUT -s {{ trigger.source_ip }} -j DROP && logger 'Blocked {{ trigger.source_ip }} via StackStorm'"

notification:
  on-complete:
    routes:
      - "slack"
    message: "Auto-remediation: Blocked {{ trigger.source_ip }} after {{ trigger.count }} failed SSH attempts"
```

This rule monitors authentication logs, counts failed login attempts per source IP within a time window, and automatically adds a firewall rule when the threshold is exceeded. The security team gets notified via Slack.

## IRIS: Collaborative Incident Response Platform

IRIS is purpose-built for digital forensics and incident response (DFIR) teams. While Shuffle automates workflows and StackStorm responds to events, IRIS provides the investigative workspace where analysts document evidence, track timelines, and collaborate on active cases.

### Key Features

- **Case management**: Create, organize, and track security investigations with full audit trails
- **Timeline reconstruction**: Build chronological views of attacker activity across systems
- **Evidence tracking**: Catalog and hash digital evidence with chain-of-custody documentation
- **IOC management**: Store and correlate indicators of compromise across cases
- **Analyst collaboration**: Multiple analysts can work on the same case simultaneously
- **Module system**: Python-based modules for automated analysis tasks
- **Customer management**: Multi-tenant support for MSSPs managing multiple clients
- **Reporting**: Generate professional incident reports with case data
- **MITRE ATT&CK mapping**: Tag adversary techniques per case

### Installation with Docker Compose

IRIS uses a multi-service Docker Compose setup with PostgreSQL, RabbitMQ, and Elasticsearch:

```yaml
# docker-compose.yml for IRIS
services:
  rabbitmq:
    extends:
      file: docker-compose.base.yml
      service: rabbitmq

  db:
    extends:
      file: docker-compose.base.yml
      service: db
    image: ghcr.io/dfir-iris/iriswebapp_db:v2.4.20
    volumes:
      - db_data:/var/lib/postgresql/data

  elasticsearch:
    extends:
      file: docker-compose.base.yml
      service: elasticsearch
    volumes:
      - es_data:/usr/share/elasticsearch/data

  iris-web:
    image: ghcr.io/dfir-iris/iris-web:v2.4.20
    ports:
      - "443:443"
    depends_on:
      - rabbitmq
      - db
      - elasticsearch
    environment:
      - IRIS_UPSTREAM_SERVER=app
    volumes:
      - iris_data:/home/iris/data
    restart: unless-stopped

  app:
    image: ghcr.io/dfir-iris/iris-web:v2.4.20
    depends_on:
      - rabbitmq
      - db
      - elasticsearch
    environment:
      - DOCKERIZED=1
      - IRIS_SECRET_KEY=change-me-to-a-secure-random-string
      - IRIS_UPSTREAM_SERVER=app
    restart: unless-stopped

volumes:
  db_data:
  es_data:
  iris_data:
```

Clone the repository and start:

```bash
git clone https://github.com/dfir-iris/iris-web.git
cd iris-web
# Create .env file with your configuration
docker compose up -d
```

Access the web interface at `https://localhost:443`. The default admin credentials are `administrator` / `ChangeMe!`.

### Case Workflow

A typical IRIS investigation follows this pattern:

1. **Create case**: Define scope, assign analysts, set classification
2. **Add assets**: Document affected systems with their IP addresses, hostnames, and OS details
3. **Collect IOCs**: Add indicators (file hashes, IP addresses, domains, URLs) observed during investigation
4. **Build timeline**: Create events with timestamps showing attacker progression
5. **Link evidence**: Attach forensic artifacts, screenshots, and log excerpts to timeline events
6. **Run modules**: Execute automated analysis modules to enrich IOCs and correlate across cases
7. **Generate report**: Export a professional incident report for stakeholders

IRIS shines when your team needs to document the "what happened" and "how" of a security incident with enough detail to support legal proceedings or regulatory reporting.

## Comparison: When to Choose Each Platform

| Use Case | Best Choice | Why |
|----------|------------|-----|
| Build visual security playbooks without coding | Shuffle SOAR | Drag-and-drop workflow editor, 300+ integrations |
| Auto-remediate infrastructure events | StackStorm | Mature rules engine, 6,000+ actions, ChatOps |
| Manage incident investigations and evidence | IRIS | Purpose-built DFIR case management |
| Connect SIEM alerts to ticketing systems | Shuffle SOAR | Native webhook triggers, OpenAPI import |
| Automated server remediation | StackStorm | Event-driven architecture, SSH actions |
| Digital forensics documentation | IRIS | Timeline reconstruction, evidence hashing |
| MSSP with multiple clients | IRIS | Built-in customer management and RBAC |
| DevOps team needing security automation | StackStorm | Bridges DevOps and security workflows |
| SOC analyst workflow automation | Shuffle SOAR | Analyst-friendly visual builder |
| Threat hunting collaboration | IRIS | Shared case workspace with IOC correlation |

Many organizations run multiple platforms together. A common pattern is using **StackStorm for infrastructure-level automation** (auto-scaling, service restarts, log rotation), **Shuffle SOAR for security-specific workflows** (alert enrichment, IOC lookups, ticket creation), and **IRIS as the case management system** where all automated actions are logged and analysts collaborate on investigations.

For teams already running a self-hosted [threat intelligence platform](../misp-vs-opencti-vs-intelowl-self-hosted-threat-intelligence-guide-2026/) or [SIEM solution](../self-hosted-siem-wazuh-security-onion-elastic-guide/), adding a SOAR platform completes the security operations triad: detect, analyze, respond.

## Integration Patterns

### Shuffle SOAR + IRIS

The most natural pairing: Shuffle handles the automated response while IRIS manages the human investigation. When Shuffle's phishing detection workflow identifies a malicious email, it can automatically:

1. Create a new case in IRIS via the REST API
2. Populate the case with extracted IOCs (sender IP, malicious URLs, attachment hashes)
3. Assign the case to the appropriate analyst based on severity
4. Add initial timeline events with timestamps

The analyst then picks up the case in IRIS, adds forensic findings, and documents the investigation — while Shuffle continues to automate containment actions in the background.

### StackStorm + Shuffle SOAR

StackStorm excels at the "sense" layer — detecting events from infrastructure monitoring, log aggregation, and network sensors. Shuffle SOAR excels at the "act" layer — orchestrating multi-step security responses. Together:

1. StackStorm detects anomalous process execution on a server
2. StackStorm triggers a Shuffle webhook with event details
3. Shuffle runs a playbook: isolate host, collect memory dump, scan for IOCs
4. Shuffle updates the StackStorm event with results
5. StackStorm posts summary to the team's Slack channel

This pattern lets each platform do what it does best without duplicating integration work.

## Resource Requirements

| Platform | Minimum RAM | CPU | Disk | Notes |
|----------|------------|-----|------|-------|
| Shuffle SOAR | 4 GB | 2 cores | 20 GB | Lightweight, scales with workflow count |
| StackStorm | 8 GB | 4 cores | 40 GB | MongoDB + RabbitMQ + multiple services |
| IRIS | 8 GB | 4 cores | 50 GB | PostgreSQL + Elasticsearch + RabbitMQ |

All three platforms run comfortably on a single mid-range server for small to medium teams. Shuffle has the lightest footprint, while IRIS's Elasticsearch requirement pushes its resource needs higher for environments processing large volumes of case data.

## FAQ

### Is Shuffle SOAR production-ready?

Yes. Shuffle SOAR is actively maintained (updated April 2026) and used by security teams worldwide. Its AGPL-3.0 license ensures the code remains open source. The platform handles enterprise-scale workloads with its multi-tenancy support and Orborus worker nodes for distributed execution.

### Can StackStorm replace a commercial SOAR platform?

StackStorm can replace many SOAR functions, particularly for infrastructure automation and event-driven responses. However, it lacks the visual workflow builder that commercial SOAR platforms provide. If your team values visual playbook design, Shuffle SOAR is a closer match. StackStorm's strength is its maturity, extensive integration pack library, and superior ChatOps capabilities.

### How does IRIS compare to TheHive for case management?

Both IRIS and TheHive are excellent incident response case management platforms. IRIS has a more modern web interface, active development (updated April 2026), and native support for timeline reconstruction with visual evidence linking. TheHive's open-source version has transitioned to a commercial distribution model, making IRIS an attractive fully open-source alternative for DFIR teams.

### Can I run all three platforms together?

Absolutely. They serve complementary purposes: StackStorm for event detection and infrastructure automation, Shuffle SOAR for security workflow orchestration, and IRIS for case management and investigation documentation. Many organizations run all three, connecting them via webhooks and REST APIs to create a complete security automation pipeline.

### Do these platforms support MITRE ATT&CK framework mapping?

Yes. Shuffle SOAR has native MITRE ATT&CK integration, allowing you to tag workflows with specific tactics and techniques. IRIS also supports MITRE ATT&CK mapping at the case level. StackStorm supports it through community integration packs that can query the ATT&CK API and tag events accordingly.

### What authentication methods do these platforms support?

Shuffle SOAR supports local accounts, SSO via OpenID Connect, and API keys. StackStorm supports LDAP, Active Directory, and local authentication with RBAC. IRIS supports local accounts and can integrate with external identity providers via its module system. All three provide API token authentication for programmatic access.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Shuffle SOAR vs StackStorm vs IRIS: Self-Hosted Security Automation & Incident Response Guide 2026",
  "description": "Compare Shuffle SOAR, StackStorm, and IRIS — three powerful open-source platforms for self-hosted security automation, incident response, and event-driven orchestration.",
  "datePublished": "2026-04-20",
  "dateModified": "2026-04-20",
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
