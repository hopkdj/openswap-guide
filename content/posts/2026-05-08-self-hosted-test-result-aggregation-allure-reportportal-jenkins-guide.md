---
title: "Self-Hosted Test Result Aggregation: Allure vs ReportPortal vs Jenkins XUnit"
date: "2026-05-08"
draft: false
tags: ["testing", "ci-cd", "test-reporting", "quality-assurance", "automation"]
---

Test result aggregation platforms collect, organize, and visualize test outcomes from your CI/CD pipelines. Instead of scrolling through thousands of lines of console output, these tools provide dashboards showing pass rates, flaky tests, historical trends, and detailed failure analysis.

In this guide, we compare three self-hosted test reporting platforms: **Allure Report**, **ReportPortal**, and **Jenkins XUnit with Blue Ocean** — each offering a different approach to test result visualization and analysis.

## Comparison Overview

| Feature | Allure Report | ReportPortal | Jenkins XUnit |
|---------|---------------|--------------|---------------|
| **GitHub Stars** | 5,400+ | 2,000+ | Built into Jenkins |
| **Language** | Java/JavaScript | Java | Java |
| **Architecture** | Static HTML reports | Server + agent architecture | Jenkins plugin |
| **Deployment** | Static files (any web server) | Docker Compose / Kubernetes | Jenkins server |
| **Historical Trends** | Yes (with Jenkins plugin) | Yes (built-in) | Yes (built into Jenkins) |
| **Real-time Results** | No (post-run only) | Yes (streaming) | Yes (during build) |
| **Test Framework Support** | JUnit, TestNG, pytest, Mocha, Jasmine, Cucumber, SpecFlow | JUnit, TestNG, pytest, NUnit, Cucumber, Robot Framework | JUnit, NUnit, xUnit, pytest (via plugins) |
| **Screenshot Attachment** | Yes | Yes | Via plugins |
| **Video Attachment** | Yes | Yes | Via plugins |
| **Flaky Test Detection** | Limited (via plugins) | Yes (built-in ML) | Limited |
| **Auto-analysis** | No | Yes (ML-based failure classification) | No |
| **Team Dashboards** | Basic | Advanced (launch-level, user-level) | Pipeline-level only |
| **API Access** | No (static files) | Yes (REST API) | Yes (Jenkins API) |
| **Integrations** | Jenkins, GitLab CI, GitHub Actions, TeamCity | Jenkins, GitLab CI, GitHub Actions, Azure DevOps | Jenkins ecosystem |
| **Database Required** | No | PostgreSQL + Elasticsearch | Jenkins internal |
| **License** | Apache 2.0 | Apache 2.0 | MIT |

## Allure Report

**Allure Report** is the most widely adopted open-source test reporting framework. It generates rich, interactive HTML reports from test results produced by virtually any testing framework through language-specific adapters.

### Key Features

- **Multi-language support** — adapters for Java, Python, JavaScript, Ruby, PHP, Swift, C#, Go
- **Rich test views** — behaviors, packages, suites, timeline, categories, retries
- **Test case history** — trend charts showing pass/fail rates over time
- **Flexible categorization** — group failures by product defect, test defect, or flaky test
- **Attachment support** — screenshots, logs, videos, custom files embedded in reports
- **Zero server overhead** — generates static HTML, no database needed

### Docker Compose for Allure Server (Optional)

While Allure generates static files, you can serve them via a simple web server:

```yaml
services:
  allure-server:
    image: frankescobar/allure-docker-service:latest
    restart: unless-stopped
    ports:
      - "5050:5050"
      - "4040:4040"
    environment:
      - CHECK_RESULTS_EVERY_SECONDS=3
      - KEEP_HISTORY=1
      - KEEP_HISTORY_LATEST=25
      - URL_PREFIX=
      - SECURITY_ENABLED=false
    volumes:
      - ./allure-results:/app/allure-results
      - ./allure-reports:/app/default-reports
      - ./projects:/app/projects
```

### Generating Reports with Allure

```bash
# Install the adapter for your test framework
pip install allure-pytest  # Python
npm i -D allure-commandline  # JavaScript/TypeScript

# Run tests and generate results
pytest --alluredir=allure-results

# Generate the report
allure generate allure-results -o allure-report --clean

# Open the report in a browser
allure open allure-report
# Or serve with any static file server
python3 -m http.server 8080 --directory allure-report
```

### CI/CD Integration

```yaml
# GitHub Actions
- name: Generate Allure Report
  uses: simple-elf/allure-report-action@master
  if: always()
  with:
    allure_results: allure-results
    allure_report: allure-report

# GitLab CI
allure-report:
  stage: report
  image: frankescobar/allure-docker-service
  script:
    - allure generate allure-results -o allure-report --clean
  artifacts:
    paths:
      - allure-report/
    reports:
      html: allure-report/index.html
```

### When to Choose Allure

Choose Allure when you need **beautiful, detailed test reports** with minimal infrastructure overhead. The static HTML output means you can host reports anywhere — S3, GitHub Pages, or any web server. It's ideal for teams that want rich test documentation with screenshots, logs, and failure categorization without running a dedicated server.

## ReportPortal

**ReportPortal** is a full-featured test analytics platform with auto-analysis, flaky test detection, and collaborative debugging. Unlike Allure's static reports, ReportPortal runs as a server that receives test results in real-time.

### Key Features

- **Real-time streaming** — test results appear in the dashboard as tests execute
- **Auto-analysis** — ML-powered failure classification reduces manual triage by 60–80%
- **Flaky test detection** — identifies tests with inconsistent results across runs
- **Launch comparison** — side-by-side comparison of different test runs
- **Collaborative debugging** — assign defects, add comments, link to issue trackers
- **User management** — role-based access control, personal and project dashboards
- **Widget system** — customizable dashboards with 20+ built-in widgets

### Docker Compose Configuration

```yaml
services:
  reportportal:
    image: reportportal/service-api:5.12.0
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - RP_SERVER_PORT=8080
      - RP_DB_HOST=postgres
      - RP_DB_NAME=reportportal
      - RP_DB_USER=rpuser
      - RP_DB_PASSWORD=rppassword
      - RP_AMQP_HOST=rabbitmq
      - RP_AMQP_PORT=5672
      - RP_AMQP_USER=guest
      - RP_AMQP_PASSWORD=guest
      - RP_INDEXING_HOST=elasticsearch
      - RP_INDEXING_PORT=9200
    depends_on:
      postgres:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
      elasticsearch:
        condition: service_healthy

  postgres:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      - POSTGRES_DB=reportportal
      - POSTGRES_USER=rpuser
      - POSTGRES_PASSWORD=rppassword
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U rpuser"]
      interval: 10s
      timeout: 5s
      retries: 5

  rabbitmq:
    image: rabbitmq:3-management-alpine
    restart: unless-stopped
    environment:
      - RABBITMQ_DEFAULT_USER=guest
      - RABBITMQ_DEFAULT_PASS=guest
    volumes:
      - rabbitmqdata:/var/lib/rabbitmq
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "check_port_connectivity"]
      interval: 10s
      timeout: 5s
      retries: 5

  elasticsearch:
    image: elasticsearch:8.11.0
    restart: unless-stopped
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms512m -Xmx512m
    volumes:
      - esdata:/usr/share/elasticsearch/data
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9200/_cluster/health"]
      interval: 10s
      timeout: 5s
      retries: 10

volumes:
  pgdata:
  rabbitmqdata:
  esdata:
```

### Integration with pytest

```bash
pip install reportportal-client pytest-reportportal

# Configure in pytest.ini
[pytest]
rp_endpoint = http://localhost:8080
rp_project = default_personal
rp_launch = My Test Suite
rp_launch_description = Automated regression tests
rp_launch_attributes = regression smoke

# Run tests — results stream to ReportPortal in real-time
pytest --reportportal
```

### When to Choose ReportPortal

Choose ReportPortal when you need **advanced test analytics** with auto-analysis, flaky test detection, and team collaboration features. It's ideal for large QA teams running thousands of tests daily, where manual failure triage is a bottleneck. The ML-powered auto-analysis learns from your team's classifications and improves over time.

## Jenkins XUnit with Blue Ocean

**Jenkins XUnit** is the built-in test reporting plugin for Jenkins, providing JUnit-style test result aggregation with trend visualization. Combined with Blue Ocean, it offers a modern pipeline visualization with integrated test results.

### Key Features

- **Zero additional infrastructure** — runs within existing Jenkins instance
- **Pipeline integration** — test results appear inline with build stages
- **Trend visualization** — pass/fail/skip charts over build history
- **Failure drill-down** — navigate from trend chart to individual test failures
- **JUnit XML compatibility** — works with any test framework that outputs JUnit XML
- **Blue Ocean UI** — modern, visual pipeline view with test result overlay

### Jenkins Pipeline Configuration

```groovy
pipeline {
    agent any
    
    stages {
        stage('Test') {
            steps {
                sh 'pytest --junitxml=test-results.xml'
            }
            post {
                always {
                    junit testResults: 'test-results.xml',
                          allowEmptyResults: true,
                          healthScaleFactor: 1.0
                }
            }
        }
        
        stage('Report') {
            steps {
                // Generate Allure report as additional view
                allure([
                    includeProperties: false,
                    jdk: '',
                    properties: [],
                    reportBuildPolicy: 'ALWAYS',
                    results: [[path: 'allure-results']]
                ])
            }
        }
    }
}
```

### When to Choose Jenkins XUnit

Choose Jenkins XUnit when you're **already running Jenkins** and want basic test result tracking without additional infrastructure. It provides the simplest path to test visibility — just add a `junit` step to your pipeline. However, it lacks the rich visualization and analytics of dedicated reporting platforms.

## Choosing the Right Test Reporting Platform

| Use Case | Best Choice | Why |
|----------|-------------|-----|
| Quick setup, no server | Allure | Static HTML, zero infrastructure |
| Team collaboration, auto-analysis | ReportPortal | ML-powered triage, real-time streaming |
| Jenkins-native reporting | Jenkins XUnit | Built-in, no extra components |
| Multiple test frameworks | Allure | Most language adapters available |
| Large-scale test suites (10K+) | ReportPortal | Streaming, auto-analysis reduces triage |
| Minimal resource usage | Allure | No database, no background services |
| Historical trend analysis | ReportPortal | Built-in launch comparison and trends |

## Why Self-Host Test Reporting?

Self-hosting your test result aggregation platform provides significant advantages for development teams:

**Complete test data ownership.** Test results contain sensitive information about your codebase, infrastructure endpoints, and security test outcomes. Self-hosting ensures this data stays within your organization. Cloud-based test reporting services may retain your test data indefinitely.

**Deep CI/CD integration.** Self-hosted platforms integrate directly with your Jenkins, GitLab, or GitHub Actions infrastructure. Test results appear alongside build logs, deployment statuses, and code coverage metrics — creating a unified view of code quality.

**Historical trend analysis.** Long-running test data reveals patterns: flaky tests that pass intermittently, regression patterns after specific commits, performance degradation over time. Self-hosted platforms let you retain unlimited history without per-launch storage fees.

**Cost efficiency at scale.** Commercial test management platforms charge per user, per test run, or per test case. At 1,000+ test runs per day across multiple projects, these costs escalate quickly. Self-hosted platforms run on your CI/CD infrastructure with no per-test fees.

**Custom analysis and automation.** Self-hosted platforms give you direct database access (ReportPortal) or file system access (Allure) for custom analysis. Build automated alerts for flaky test thresholds, generate executive dashboards, or integrate with internal issue tracking systems.

For related reading, see our [load testing platform comparison](../k6-vs-locust-vs-gatling-load-testing-guide-2026/) and [container image scanning guide](../2026-04-24-self-hosted-container-image-scanning-trivy-grype-clair-anchore-guide-2026/). If you're building a complete CI/CD pipeline, our [synthetic monitoring guide](../2026-04-28-gatus-vs-k6-vs-uptime-kuma-self-hosted-synthetic-monitoring-guide-2026/) covers the testing infrastructure layer.

## FAQ

### Can I use Allure with ReportPortal?

Yes. Allure generates detailed test reports from test results, while ReportPortal provides real-time analytics and auto-analysis. Some teams use Allure for detailed per-run documentation and ReportPortal for cross-run trend analysis. Run your tests with the Allure adapter, then send the same results to ReportPortal using its agent.

### Does ReportPortal require Elasticsearch for small teams?

Elasticsearch is required for the auto-analysis feature. If you disable auto-analysis, ReportPortal can run with just PostgreSQL and RabbitMQ. However, the search and filtering capabilities will be limited. For teams under 10 users running fewer than 1,000 tests per day, the full stack (PostgreSQL + Elasticsearch + RabbitMQ) runs comfortably on 4 CPU cores and 8 GB RAM.

### How do I migrate from a commercial test management tool to a self-hosted platform?

Export your test cases and historical results in JUnit XML format (most commercial tools support this). Import the XML into Allure for immediate static reports, or use ReportPortal's REST API to programmatically upload results. Historical trend data will start accumulating from your first self-hosted run.

### Which test frameworks are supported by these platforms?

Allure supports the widest range: JUnit 4/5, TestNG, pytest, Mocha, Jasmine, Cucumber (Java/JS/Ruby), NUnit, SpecFlow, Behave, and more via community adapters. ReportPortal supports JUnit, TestNG, pytest, NUnit, Cucumber, and Robot Framework through its agent ecosystem. Jenkins XUnit accepts any JUnit XML output, which most test frameworks can produce.

### How do I handle parallel test execution with these platforms?

Allure supports parallel execution by writing results to a shared directory — each test process writes to a unique subdirectory, and Allure merges them during report generation. ReportPortal handles parallel execution natively through its agent, which streams results to the server with unique launch IDs. Jenkins XUnit merges JUnit XML files from parallel stages using wildcard patterns.

### Can I integrate test reports with Slack or email notifications?

ReportPortal has built-in Slack and email integration with configurable triggers (launch completed, failures detected, flaky test threshold exceeded). Allure reports can be linked in Slack messages after CI/CD builds complete. Jenkins XUnit integrates with Jenkins' built-in notification system (email, Slack plugin, webhook).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Test Result Aggregation: Allure vs ReportPortal vs Jenkins XUnit",
  "description": "Compare three self-hosted test result aggregation platforms — Allure Report, ReportPortal, and Jenkins XUnit. Includes Docker Compose configs and CI/CD integration examples.",
  "datePublished": "2026-05-08",
  "dateModified": "2026-05-08",
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
