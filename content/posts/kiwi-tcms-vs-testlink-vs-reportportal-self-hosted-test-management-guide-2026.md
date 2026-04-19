---
title: "Kiwi TCMS vs TestLink vs ReportPortal: Best Self-Hosted Test Management Tools 2026"
date: 2026-04-19
tags: ["comparison", "guide", "self-hosted", "testing", "qa", "test-management"]
draft: false
description: "Compare Kiwi TCMS, TestLink, and ReportPortal — the top open-source, self-hosted test management platforms. Docker deployment guides, feature comparison, and decision matrix for QA teams."
---

Test management is one of those areas where SaaS tools dominate the conversation — TestRail, Qase, Zephyr — but self-hosted open-source alternatives have matured significantly. Whether you're running a QA lab with air-gapped systems, managing compliance requirements that demand data sovereignty, or simply want full control over your test data, the self-hosted path is viable.

This guide compares the three most capable open-source test management platforms: **Kiwi TCMS**, **TestLink**, and **ReportPortal**. We'll cover features, deployment, API integrations, and help you choose the right tool for your team. For related reading, check out our [self-hosted CI/CD guide](../2026-04-19-woodpecker-ci-vs-drone-ci-vs-gitea-actions-self-hosted-cicd-guide-2026/) for pipeline integration tips and the [browser automation server comparison](../self-hosted-browser-automation-servers-browserless-playwright-selenium-grid-guide-2026/) for end-to-end testing infrastructure.

## Why Self-Host Your Test Management

Test case data contains sensitive information about your product: feature roadmaps, known defects, security test procedures, and release timelines. Keeping this data on-premises offers several advantages:

- **Data sovereignty** — test data never leaves your infrastructure, critical for healthcare, finance, and government sectors
- **No per-user licensing** — open-source tools scale without seat-based pricing
- **Deep integrations** — self-hosted tools can connect directly to your internal CI/CD, issue trackers, and artifact registries without traversing public APIs
- **Custom workflows** — full access to source code means you can adapt the tool to your exact processes
- **Offline availability** — air-gapped environments can still run full test management operations

## Kiwi TCMS — Modern Python-Based Test Management

[Kiwi TCMS](https://kiwitcms.org/) is an open-source test management system written in Python (Django). With over 2 million Docker pulls and 1,183 GitHub stars, it's the most actively maintained self-hosted test management platform today.

### Key Features

- **Test plan management** — organize test cases into hierarchical test plans with version tracking
- **Test execution tracking** — record pass/fail/skipped results with attachments and comments
- **Bug tracker integration** — native connectors for GitHub, GitLab, Jira, and Bugzilla
- **REST API** — full JSON-RPC API for automation and CI/CD pipeline integration
- **Multi-language support** — translations for 20+ languages via Crowdin
- **Role-based access** — granular permissions for testers, reviewers, and administrators
- **XML/CSV import/export** — migrate from TestLink, TestRail, or spreadsheets
- **Plugin architecture** — extend functionality with custom plugins

### Quick Stats

| Metric | Value |
|--------|-------|
| GitHub Stars | 1,183 |
| Primary Language | Python (Django) |
| Last Updated | April 17, 2026 |
| License | GPLv3 |
| Database | MariaDB/MySQL |
| Docker Image | `pub.kiwitcms.eu/kiwitcms/kiwi:latest` |

### Docker Compose Deployment

```yaml
version: '2'

services:
    db:
        container_name: kiwi_db
        image: mariadb:latest
        command:
            --character-set-server=utf8mb4
            --collation-server=utf8mb4_unicode_ci
        volumes:
            - db_data:/var/lib/mysql
        restart: always
        environment:
            MYSQL_ROOT_PASSWORD: kiwi-secure-password
            MYSQL_DATABASE: kiwi
            MYSQL_USER: kiwi
            MYSQL_PASSWORD: kiwi-secure-password

    web:
        container_name: kiwi_web
        depends_on:
            - db
        restart: always
        image: pub.kiwitcms.eu/kiwitcms/kiwi:latest
        ports:
            - "80:8080"
            - "443:8443"
        volumes:
            - uploads:/Kiwi/uploads:Z
        environment:
            KIWI_DB_HOST: db
            KIWI_DB_PORT: 3306
            KIWI_DB_NAME: kiwi
            KIWI_DB_USER: kiwi
            KIWI_DB_PASSWORD: kiwi-secure-password
        cap_drop:
            - ALL

volumes:
    db_data:
    uploads:
```

Deploy with:

```bash
mkdir -p kiwi-tcms && cd kiwi-tcms
# Save the compose file as docker-compose.yml
docker compose up -d
# Access at http://localhost:80
# Default admin credentials: admin / admin
```

Kiwi TCMS also supports integration with popular test automation frameworks. You can submit test results directly from your CI pipeline using the JSON-RPC API:

```bash
# Example: Create a test run via Kiwi TCMS API
curl -X POST http://localhost:80/json-rpc/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "TestRun.create",
    "params": {
      "plan": 42,
      "summary": "Regression run - Sprint 14",
      "manager": "admin"
    },
    "id": 1
  }'
```

## TestLink — The Veteran Open-Source Test Manager

[TestLink](https://testlink.org/) is one of the oldest open-source test management tools, written in PHP. With 1,593 GitHub stars, it has been the default choice for teams needing test management since the mid-2000s.

### Key Features

- **Requirements management** — link test cases to product requirements for traceability
- **Test case versioning** — track changes to test cases over time
- **Test project hierarchy** — organize by project, test suite, and test case
- **Multiple result states** — pass, fail, blocked, not run, and custom statuses
- **Custom fields** — add project-specific metadata to test cases
- **Reports and metrics** — built-in dashboards for test coverage and execution trends
- **User management** — role-based access with guest, tester, senior tester, and admin roles
- **Third-party integrations** — plugins for Jira, Mantis, Bugzilla, and more

### Quick Stats

| Metric | Value |
|--------|-------|
| GitHub Stars | 1,593 |
| Primary Language | PHP |
| Last Updated | December 8, 2025 |
| License | GPL |
| Database | MySQL/MariaDB |
| Docker Image | Community-maintained |

### Docker Compose Deployment

TestLink does not provide an official Docker Compose file, but it can be deployed using the Bitnami image:

```yaml
version: '3.8'

services:
  mariadb:
    image: docker.io/bitnami/mariadb:11.4
    environment:
      - ALLOW_EMPTY_PASSWORD=yes
      - MARIADB_USER=bn_testlink
      - MARIADB_DATABASE=bitnami_testlink
    volumes:
      - mariadb_data:/bitnami/mariadb

  testlink:
    image: docker.io/bitnami/testlink:1.9
    ports:
      - '8080:8080'
      - '8443:8443'
    environment:
      - ALLOW_EMPTY_PASSWORD=yes
      - TESTLINK_DATABASE_HOST=mariadb
      - TESTLINK_DATABASE_PORT_NUMBER=3306
      - TESTLINK_DATABASE_USER=bn_testlink
      - TESTLINK_DATABASE_NAME=bitnami_testlink
    volumes:
      - testlink_data:/bitnami/testlink
    depends_on:
      - mariadb

volumes:
  mariadb_data:
    driver: local
  testlink_data:
    driver: local
```

Deploy with:

```bash
mkdir -p testlink && cd testlink
# Save the compose file as docker-compose.yml
docker compose up -d
# Access at http://localhost:8080
# Default admin: user / bitnami
```

## ReportPortal — Test Results Aggregation and Analysis

[ReportPortal](https://reportportal.io/) takes a different approach — rather than managing test cases, it focuses on **aggregating, analyzing, and visualizing test results** from multiple sources. With 1,979 GitHub stars, it's the most popular of the three tools covered here.

ReportPortal is designed to complement your existing test automation frameworks (Selenium, Cypress, Playwright, JUnit, pytest, etc.) by collecting test results and providing intelligent analysis, auto-triage, and historical trends.

### Key Features

- **Multi-framework support** — agent libraries for Java, Python, .NET, JavaScript, Ruby, and more
- **Auto-analysis** — ML-powered log analysis to automatically classify test failures
- **Defect grouping** — clusters similar failures across test runs to reduce noise
- **Historical trends** — track flaky tests, execution time regression, and pass rate trends
- **Real-time dashboards** — live test execution monitoring with customizable widgets
- **Plugin ecosystem** — integrations with Jira, Slack, email, and S3/MinIO storage
- **Multi-project support** — manage multiple projects and teams from a single instance
- **Fine-grained permissions** — project roles, user filters, and team-based access control

### Quick Stats

| Metric | Value |
|--------|-------|
| GitHub Stars | 1,979 |
| Primary Language | Java (services), JavaScript (UI) |
| Last Updated | April 9, 2026 |
| License | Apache 2.0 |
| Database | PostgreSQL |
| Dependencies | PostgreSQL, RabbitMQ, OpenSearch, Traefik |

### Docker Compose Deployment

ReportPortal requires the most infrastructure — it runs as a microservices architecture:

```yaml
version: '3.8'

services:
  gateway:
    image: traefik:v2.11.32
    ports:
      - "8080:8080"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command:
      - --providers.docker=true
      - --entrypoints.web.address=:8080
      - --entrypoints.websecure.address=:443

  postgres:
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: rpuser
      POSTGRES_PASSWORD: rppass
      POSTGRES_DB: reportportal
    volumes:
      - postgres_data:/var/lib/postgresql/data

  rabbitmq:
    image: rabbitmq:4-management
    environment:
      RABBITMQ_DEFAULT_USER: rabbitmq
      RABBITMQ_DEFAULT_PASS: rabbitmq

  opensearch:
    image: opensearchproject/opensearch:2.19.0
    environment:
      discovery.type: single-node
      DISABLE_SECURITY_PLUGIN: "true"
      OPENSEARCH_JAVA_OPTS: -Xms512m -Xmx512m
    volumes:
      - opensearch_data:/usr/share/opensearch/data

  uat:
    image: reportportal/service-authorization:5.12.3
    depends_on: [postgres]
    environment:
      RP_DB_HOST: postgres
      RP_DB_USER: rpuser
      RP_DB_PASS: rppass
      RP_DB_NAME: reportportal

  api:
    image: reportportal/service-api:5.12.3
    depends_on: [postgres, rabbitmq]
    environment:
      RP_DB_HOST: postgres
      RP_DB_USER: rpuser
      RP_DB_PASS: rppass
      RP_DB_NAME: reportportal
      RP_AMQP_HOST: rabbitmq

  ui:
    image: reportportal/service-ui:5.12.3
    depends_on: [uat, api]

volumes:
  postgres_data:
  opensearch_data:
```

Deploy with:

```bash
mkdir -p reportportal && cd reportportal
# Save the compose file as docker-compose.yml
docker compose up -d
# Access at http://localhost:8080
# Default admin: default / 1q2w3e
```

For production deployments, ReportPortal provides a full installer script:

```bash
curl -sSL https://raw.githubusercontent.com/reportportal/reportportal/master/install.sh \
  -o install.sh
chmod +x install.sh
./install.sh
```

### Integrating Test Frameworks

ReportPortal uses "agent" libraries to collect test results. Here's how to integrate with pytest:

```bash
pip install pytest-reportportal
```

Then configure `pytest.ini`:

```ini
[pytest]
rp_endpoint = http://localhost:8080
rp_uuid = your-api-uuid-here
rp_launch = MyTestLaunch
rp_project = default_personal
```

Run tests:

```bash
pytest --reportportal tests/
```

Results appear in the ReportPortal UI with full logs, attachments, and auto-analysis.

## Feature Comparison

| Feature | Kiwi TCMS | TestLink | ReportPortal |
|---------|-----------|----------|--------------|
| **Primary Focus** | Test case management | Test case management | Test result analysis |
| **Language** | Python (Django) | PHP | Java / JavaScript |
| **Database** | MariaDB | MariaDB | PostgreSQL |
| **Docker Support** | Official compose | Bitnami image | Official compose |
| **REST API** | Full JSON-RPC | XML-RPC | REST API |
| **Bug Tracker Integration** | GitHub, GitLab, Jira, Bugzilla | Jira, Mantis, Bugzilla | Jira (plugin) |
| **Test Automation Integration** | API-based | Limited | Agent libraries (6+ frameworks) |
| **Auto-Analysis** | No | No | Yes (ML-powered) |
| **Requirements Traceability** | Yes | Yes | No |
| **Multi-language UI** | 20+ languages | Multiple | English |
| **Flaky Test Detection** | No | No | Yes |
| **Historical Trends** | Basic | Basic | Advanced |
| **Resource Requirements** | Low (1 GB RAM) | Low (1 GB RAM) | High (4+ GB RAM) |
| **GitHub Stars** | 1,183 | 1,593 | 1,979 |
| **License** | GPLv3 | GPL | Apache 2.0 |

## Which Tool Should You Choose?

### Choose Kiwi TCMS if:
- You need a **modern, actively maintained** test case management system
- Your team works primarily in **Python** and wants native Django ecosystem integration
- You want **simple deployment** — just two containers (web + database)
- You need strong **bug tracker integration** out of the box
- You're migrating from TestLink and want an **import tool**

### Choose TestLink if:
- You need **requirements traceability** as a core workflow
- Your team is already familiar with the **classic TestLink interface**
- You want the **most battle-tested** option (20+ years of development)
- You need **custom fields** and flexible test case metadata
- Resource constraints are tight (runs on minimal hardware)

### Choose ReportPortal if:
- You have **heavy test automation** and need result aggregation
- You want **automatic failure analysis** and flaky test detection
- Your team runs tests across **multiple frameworks** (Java, Python, JS, etc.)
- You need **real-time dashboards** for CI/CD pipeline visibility
- You have infrastructure to support a **microservices deployment**

### Hybrid Approach

Many teams combine tools: use **Kiwi TCMS** or **TestLink** for test case design and planning, then feed execution results into **ReportPortal** for analysis and trending. This gives you the structured test management of the first two tools with the analytical power of ReportPortal. Pair this setup with our [code quality scanning guide](../sonarqube-vs-semgrep-vs-codeql-self-hosted-code-quality-guide-2026/) to cover both dynamic testing (test execution) and static analysis (code scanning) in your QA workflow.

## FAQ

### What is the difference between Kiwi TCMS and ReportPortal?

Kiwi TCMS is a test case management system — you create, organize, and track test cases and test plans. ReportPortal is a test result aggregation platform — it collects results from automated test frameworks and provides analysis, auto-triage, and dashboards. They solve different problems and can be used together.

### Is TestLink still maintained in 2026?

Yes, but development has slowed. The last commit to the main TestLink repository was in December 2025. Kiwi TCMS, by contrast, has weekly releases and an active community. For new deployments, Kiwi TCMS is generally recommended over TestLink unless you have existing TestLink workflows.

### Can I import test cases from TestLink into Kiwi TCMS?

Yes. Kiwi TCMS provides a built-in TestLink import tool that reads TestLink XML exports and converts them into Kiwi TCMS test plans and test cases. The migration preserves test case hierarchy, steps, and expected results.

### Does ReportPortal replace manual test management?

No. ReportPortal is designed for **automated test result analysis**. It does not manage test cases, test plans, or manual test execution workflows. For manual testing, use Kiwi TCMS or TestLink. For automated test result visibility, add ReportPortal.

### How many resources does each tool require?

Kiwi TCMS and TestLink each need about 1 GB of RAM and a single database container. ReportPortal requires significantly more — at least 4 GB RAM for its full microservices stack (PostgreSQL, RabbitMQ, OpenSearch, and 6+ application services).

### Can these tools integrate with CI/CD pipelines?

All three support CI/CD integration. Kiwi TCMS provides a JSON-RPC API that can be called from any pipeline. TestLink supports XML-RPC for automated result submission. ReportPortal has native agent libraries for pytest, JUnit, TestNG, Cypress, Cucumber, and more, making it the most tightly integrated option.

### Are there any security considerations for self-hosting?

Yes. Always change default passwords after initial setup. Kiwi TCMS ships with `admin/admin`, TestLink with `user/bitnami`, and ReportPortal with `default/1q2w3e`. Place a reverse proxy (Nginx, Caddy, or Traefik) in front for TLS termination. Kiwi TCMS supports `cap_drop: ALL` for container hardening — enable it in production.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Kiwi TCMS vs TestLink vs ReportPortal: Best Self-Hosted Test Management Tools 2026",
  "description": "Compare Kiwi TCMS, TestLink, and ReportPortal — the top open-source, self-hosted test management platforms. Docker deployment guides, feature comparison, and decision matrix for QA teams.",
  "datePublished": "2026-04-19",
  "dateModified": "2026-04-19",
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
