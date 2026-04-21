---
title: "JaCoCo vs Coverage.py vs Istanbul/nyc: Self-Hosted Code Coverage Guide 2026"
date: 2026-04-21
tags: ["comparison", "guide", "self-hosted", "testing", "ci-cd", "code-quality"]
draft: false
description: "Compare JaCoCo, Coverage.py, and Istanbul/nyc for self-hosted code coverage. Learn how to collect, aggregate, and visualize coverage reports without relying on SaaS services like Codecov or Coveralls."
---

Code coverage is one of the most widely tracked software quality metrics. Knowing which lines, branches, and functions your tests exercise gives teams confidence when shipping changes. But sending coverage reports to cloud SaaS platforms like Codecov, Coveralls, or SonarCloud means handing your proprietary source metrics to a third party.

For organizations with compliance requirements, air-gapped networks, or simply a preference for keeping data in-house, self-hosted code coverage tooling is the answer. This guide compares the three most popular open-source coverage collectors — **JaCoCo** (Java), **Coverage.py** (Python), and **Istanbul/nyc** (JavaScript/TypeScript) — and shows you how to run them in a self-hosted CI/CD pipeline with local reporting dashboards.

## Why Self-Host Code Coverage

Running your own coverage infrastructure offers several advantages over SaaS alternatives:

- **Data sovereignty** — source-level coverage data stays within your infrastructure. No third party sees which code paths your tests hit.
- **No rate limits or quotas** — self-hosted tools process unlimited builds without per-repo or per-upload restrictions.
- **Custom retention policies** — keep coverage history for years, not months. Audit trails and compliance requirements often demand long-term data retention.
- **Offline support** — coverage collection works in air-gapped or restricted networks without external API access.
- **Cost savings** — SaaS coverage platforms charge per developer or per repository. Self-hosted tools are free and scale horizontally on your own hardware.

For teams already running self-hosted CI/CD platforms like Gitea Actions, Woodpecker CI, or Jenkins, integrating local coverage collection is a natural next step.

## JaCoCo: Java Code Coverage

[JaCoCo](https://www.jacoco.org/jacoco/) (Java Code Coverage) is the de facto standard for JVM languages. It uses Java agent instrumentation to track line, branch, and method coverage at runtime. The project has over 4,500 GitHub stars and was last updated in April 2026, demonstrating active maintenance.

### Key Features

- Bytecode instrumentation via Java agent (`-javaagent`) — no source modification needed
- Maven and Gradle plugin integration
- HTML, XML, and CSV report formats
- Branch, line, method, and class-level coverage metrics
- Multi-module project support with aggregation
- Ant integration for legacy build systems

### Docker Compose Setup for JaCoCo Reports

While JaCoCo itself is a Java library embedded in your build, you can self-host a reporting server to aggregate results from multiple builds. Here's a Docker Compose configuration using SonarQube Community Edition as the coverage dashboard:

```yaml
version: "3.8"

services:
  sonarqube:
    image: sonarqube:community
    container_name: sonarqube
    ports:
      - "9000:9000"
    environment:
      - SONAR_JDBC_URL=jdbc:postgresql://sonarqube-db:5432/sonar
      - SONAR_JDBC_USERNAME=sonar
      - SONAR_JDBC_PASSWORD=sonar_password
      - SONAR_ES_BOOTSTRAP_CHECKS_DISABLE=true
    depends_on:
      sonarqube-db:
        condition: service_healthy
    volumes:
      - sonarqube_data:/opt/sonarqube/data
      - sonarqube_extensions:/opt/sonarqube/extensions
      - sonarqube_logs:/opt/sonarqube/logs
    restart: unless-stopped

  sonarqube-db:
    image: postgres:15
    container_name: sonarqube-db
    environment:
      - POSTGRES_USER=sonar
      - POSTGRES_PASSWORD=sonar_password
      - POSTGRES_DB=sonar
    volumes:
      - postgresql_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sonar"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  sonarqube_data:
  sonarqube_extensions:
  sonarqube_logs:
  postgresql_data:
```

### Maven Configuration

Add the JaCoCo plugin to your `pom.xml`:

```xml
<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <version>0.8.12</version>
    <executions>
        <execution>
            <goals>
                <goal>prepare-agent</goal>
            </goals>
        </execution>
        <execution>
            <id>report</id>
            <phase>test</phase>
            <goals>
                <goal>report</goal>
            </goals>
        </execution>
    </executions>
</plugin>
```

Generate the report:

```bash
mvn clean test jacoco:report
```

The HTML report will be available at `target/site/jacoco/index.html`.

### Gradle Configuration

For Gradle projects, apply the plugin in `build.gradle.kts`:

```kotlin
plugins {
    jacoco
}

jacoco {
    toolVersion = "0.8.12"
    reportsDirectory.set(layout.buildDirectory.dir("reports/jacoco"))
}

tasks.test {
    finalizedBy(tasks.jacocoTestReport)
}

tasks.jacocoTestReport {
    reports {
        xml.required.set(true)
        html.required.set(true)
    }
}
```

### Setting Up Quality Gates

In SonarQube, navigate to **Quality Gates** and create a gate that enforces minimum coverage thresholds:

```
Coverage on New Code >= 80%
Line Coverage >= 75%
Branch Coverage >= 70%
```

This ensures every merge request meets your team's coverage standards. You can configure the SonarQube scanner in your CI pipeline:

```bash
sonar-scanner \
  -Dsonar.projectKey=my-java-project \
  -Dsonar.sources=src/main/java \
  -Dsonar.tests=src/test/java \
  -Dsonar.java.coveragePlugin=jacoco \
  -Dsonar.coverage.jacoco.xmlReportPaths=target/site/jacoco/jacoco.xml \
  -Dsonar.host.url=http://localhost:9000 \
  -Dsonar.token=$SONAR_TOKEN
```

## Coverage.py: Python Code Coverage

[Coverage.py](https://coverage.readthedocs.io/) (3,360 GitHub stars, last updated April 2026) is the standard coverage tool for Python. It uses Python's `sys.settrace` hook to monitor execution at the line level, making it lightweight and accurate.

### Key Features

- Line-level coverage tracking via `sys.settrace`
- Branch coverage measurement
- HTML, XML (Cobertura format), JSON, and annotated source reports
- Parallel mode for distributed test execution
- Plugin architecture for custom tracer support
- Integration with pytest via `pytest-cov` (2,031 GitHub stars)

### Installation and Basic Usage

```bash
pip install coverage pytest-cov
```

Run your test suite with coverage:

```bash
coverage run -m pytest tests/
coverage report -m
```

Generate HTML and XML reports:

```bash
coverage html -d coverage_html
coverage xml -o coverage.xml
```

### Docker-Based Coverage Collection

For Python projects running in containers, you can collect coverage during integration tests:

```yaml
version: "3.8"

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - COVERAGE_FILE=/tmp/.coverage
      - PYTHONPATH=/app
    volumes:
      - coverage_data:/tmp
    command: >
      sh -c "coverage run -m pytest /app/tests/ &&
             coverage xml -o /tmp/coverage.xml &&
             coverage html -d /tmp/coverage_html"

  coverage-reporter:
    image: python:3.12-slim
    depends_on:
      app:
        condition: service_completed_successfully
    volumes:
      - coverage_data:/coverage
      - ./reports:/output
    command: >
      sh -c "pip install coverage &&
             cd /coverage &&
             coverage combine &&
             coverage report --show-missing &&
             coverage html -d /output/html &&
             coverage xml -o /output/coverage.xml"

volumes:
  coverage_data:
```

### pytest-cov Integration

The most common way to collect Python coverage is through `pytest-cov`:

```bash
# Run with coverage on specific packages
pytest --cov=myapp --cov-report=html --cov-report=xml --cov-branch tests/

# With source directory specification
pytest --cov=myapp --cov-source=src --cov-branch \
  --cov-report=term-missing \
  tests/

# Parallel collection for CI
pytest --cov=myapp --cov-branch --cov-context=test \
  --cov-report=html \
  --numprocesses=auto tests/
```

### Combining Reports from Multiple Test Suites

For projects with separate unit and integration test suites:

```bash
# Run unit tests
coverage run --parallel-mode -m pytest tests/unit/

# Run integration tests
coverage run --parallel-mode -m pytest tests/integration/

# Combine and report
coverage combine
coverage report -m
coverage html -d combined_coverage
coverage xml -o combined_coverage.xml
```

### Pytest Configuration

Add coverage defaults to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = "--cov=myapp --cov-branch --cov-report=html --cov-report=xml"

[tool.coverage.run]
source = ["src"]
branch = true
parallel = true
omit = ["tests/*", "*/migrations/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
fail_under = 80
show_missing = true
```

## Istanbul/nyc: JavaScript and TypeScript Coverage

[Istanbul](https://istanbul.js.org/) is the leading JavaScript code coverage framework, and [nyc](https://github.com/istanbuljs/nyc) (5,759 GitHub stars, updated February 2026) is its command-line interface. Istanbul instruments code at the AST level, providing accurate statement, branch, function, and line coverage for both Node.js and browser environments.

### Key Features

- AST-based instrumentation — accurate even for transpiled code
- Supports statement, branch, function, and line coverage
- TypeScript support via `ts-node` integration
- lcov, clover, cobertura, HTML, JSON, and text reports
- Coverage threshold enforcement with exit codes
- Per-file coverage reporting
- Caching for faster repeated runs

### Installation

```bash
npm install --save-dev nyc
# or
yarn add --dev nyc
# or
pnpm add -D nyc
```

### Basic Usage with Mocha

```bash
nyc mocha tests/
nyc report --reporter=html
nyc report --reporter=lcov
```

### Jest Integration

Jest has built-in Istanbul support. Enable it in `jest.config.js`:

```javascript
module.exports = {
  testEnvironment: 'node',
  collectCoverage: true,
  collectCoverageFrom: [
    'src/**/*.{js,ts}',
    '!src/**/*.test.{js,ts}',
    '!src/**/__mocks__/**',
  ],
  coverageDirectory: 'coverage',
  coverageReporters: ['html', 'lcov', 'text-summary'],
  coverageThreshold: {
    global: {
      branches: 75,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
};
```

Run tests with coverage:

```bash
jest --coverage
```

### nyc Configuration for TypeScript Projects

For TypeScript projects using `ts-node`:

```bash
npm install --save-dev nyc ts-node @istanbuljs/nyc-config-typescript
```

Configure `nyc.config.js`:

```javascript
module.exports = {
  extends: '@istanbuljs/nyc-config-typescript',
  all: true,
  include: ['src/**/*.ts'],
  exclude: ['src/**/*.test.ts', 'src/**/__mocks__/**'],
  reporter: ['html', 'lcov', 'text'],
  reportDir: './coverage',
  tempDir: './.nyc_output',
  'check-coverage': true,
  lines: 80,
  statements: 80,
  functions: 80,
  branches: 75,
  perFile: true,
};
```

Run with:

```bash
nyc ts-mocha 'tests/**/*.ts'
```

### Docker Setup for JavaScript Coverage

Here's a Docker Compose setup that runs tests with coverage and serves the HTML report:

```yaml
version: "3.8"

services:
  test-runner:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - NODE_ENV=test
    volumes:
      - ./coverage:/app/coverage
    command: >
      sh -c "npm run test:coverage &&
             cp -r coverage/* /app/coverage/"

  coverage-viewer:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./coverage:/usr/share/nginx/html:ro
    depends_on:
      test-runner:
        condition: service_completed_successfully
    restart: unless-stopped
```

Add the test script to `package.json`:

```json
{
  "scripts": {
    "test:coverage": "nyc --reporter=html --reporter=lcov --reporter=text npm test",
    "test:coverage:ci": "nyc --reporter=cobertura --reporter=text npm test"
  }
}
```

## Comparison Table

| Feature | JaCoCo | Coverage.py | Istanbul/nyc |
|---------|--------|-------------|--------------|
| **Language** | Java, Kotlin, Scala | Python | JavaScript, TypeScript |
| **Stars** | 4,533 | 3,360 | 5,759 |
| **Last Updated** | April 2026 | April 2026 | February 2026 |
| **Instrumentation** | Bytecode agent (JVMTI) | sys.settrace hook | AST transformation |
| **Line Coverage** | Yes | Yes | Yes |
| **Branch Coverage** | Yes | Yes | Yes |
| **Function Coverage** | Method-level | Via functions extension | Yes |
| **Condition Coverage** | Yes | No | No |
| **HTML Report** | Yes | Yes | Yes |
| **XML Report** | Yes | Yes (Cobertura format) | Yes (lcov, clover) |
| **Threshold Enforcement** | Via SonarQube | `fail_under` config | `check-coverage` flag |
| **Parallel Mode** | Multi-module aggregation | `--parallel-mode` | `--all` with cache |
| **CI Integration** | Maven/Gradle plugins | pytest-cov | Jest built-in, nyc CLI |
| **Docker Support** | Via build containers | First-class | First-class |
| **Source Maps** | N/A (compiled bytecode) | N/A | Yes |
| **Minimum Version Enforcement** | Via Maven/Gradle rules | `fail_under` in config | `check-coverage` in config |

## Self-Hosted Coverage Aggregation Dashboard

Collecting coverage in individual CI runs is only half the story. To track trends, enforce quality gates, and visualize progress over time, you need a self-hosted aggregation platform. Here are the most popular options:

### SonarQube Community Edition

The most widely used self-hosted code quality platform. Supports coverage data from JaCoCo, Coverage.py (via Cobertura XML), and Istanbul (via lcov).

```bash
# Quick start with Docker
docker run -d --name sonarqube \
  -p 9000:9000 \
  -e SONAR_ES_BOOTSTRAP_CHECKS_DISABLE=true \
  sonarqube:community
```

### Codecov Self-Hosted

Codecov offers an enterprise self-hosted version that provides the same dashboard experience as their SaaS product, but running on your infrastructure.

```yaml
version: "3.8"

services:
  codecov-self-hosted:
    image: codecov/self-hosted:latest
    ports:
      - "8080:80"
    environment:
      - CODECOV_API_URL=http://localhost:8080
      - CODECOV_UPLOAD_URL=http://localhost:8080
    volumes:
      - codecov_data:/data
    restart: unless-stopped

volumes:
  codecov_data:
```

### Custom Coverage Dashboard with Grafana

For teams already running Grafana and Prometheus, you can parse coverage XML reports and push metrics to Prometheus:

```python
#!/usr/bin/env python3
"""Parse Cobertura XML and push coverage metrics to Prometheus Pushgateway."""

import xml.etree.ElementTree as ET
import urllib.request
import sys

def parse_coverage(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    lines_rate = float(root.get('line-rate', 0))
    branch_rate = float(root.get('branch-rate', 0))
    return {
        'line_coverage': round(lines_rate * 100, 2),
        'branch_coverage': round(branch_rate * 100, 2),
    }

if __name__ == '__main__':
    metrics = parse_coverage(sys.argv[1])
    payload = f"# TYPE line_coverage gauge\nline_coverage {metrics['line_coverage']}\n"
    payload += f"# TYPE branch_coverage gauge\nbranch_coverage {metrics['branch_coverage']}\n"

    req = urllib.request.Request(
        'http://pushgateway:9091/metrics/job/coverage/instance/app',
        data=payload.encode(),
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        print(f"Pushed metrics: {resp.status}")
```

## CI/CD Pipeline Integration

Here's a complete GitHub Actions / Woodpecker CI pipeline that collects coverage and uploads it to a self-hosted SonarQube:

```yaml
# Woodpecker CI pipeline (.woodpecker.yml)
pipeline:
  install:
    image: node:20
    commands:
      - npm ci

  test-coverage:
    image: node:20
    commands:
      - npx nyc --reporter=cobertura --reporter=html npm test
    when:
      branch: main

  sonar-scan:
    image: sonarsource/sonar-scanner-cli:latest
    commands:
      - >-
        sonar-scanner
        -Dsonar.projectKey=${CI_REPO_NAME}
        -Dsonar.sources=.
        -Dsonar.exclusions=**/node_modules/**,**/coverage/**
        -Dsonar.javascript.lcov.reportPaths=coverage/lcov.info
        -Dsonar.host.url=${SONAR_HOST_URL}
        -Dsonar.token=${SONAR_TOKEN}
    depends_on:
      - test-coverage
    when:
      branch: main
```

## Best Practices for Self-Hosted Coverage

1. **Set realistic thresholds** — 80% line coverage is a good baseline. Require higher thresholds (90%+) for critical modules like authentication and payment processing.
2. **Measure branch coverage, not just line coverage** — a line can be "covered" while an `if` branch inside it never executes. Branch coverage catches this gap.
3. **Fail CI on coverage regression** — configure your pipeline to block merges that decrease overall coverage percentage. Use tools like `nyc --check-coverage` or Coverage.py's `fail_under`.
4. **Exclude generated code** — never count auto-generated files (migrations, protobuf stubs, OpenAPI clients) in coverage calculations. Use `omit` / `exclude` patterns.
5. **Combine test suite coverage** — run unit, integration, and end-to-end test coverage collection separately, then merge results for a complete picture. For Python, use `coverage combine`; for JavaScript, point nyc to the same output directory.
6. **Track coverage trends over time** — a single percentage is less useful than a trend. Use your self-hosted dashboard to show coverage trajectory across sprints and releases.

For related reading, see our [SonarQube vs Semgrep vs CodeQL code quality guide](../sonarqube-vs-semgrep-vs-codeql-self-hosted-code-quality-guide-2026/) for broader static analysis strategies, the [complete CI/CD platforms comparison](../self-hosted-ci-cd-woodpecker-drone-jenkins-concourse-2026/) for pipeline setup, and our [E2E testing tools guide](../self-hosted-e2e-testing-tools-playwright-cypress-selenium-guide-2026/) for testing strategies that complement coverage metrics.

## FAQ

### What is the difference between line coverage and branch coverage?

Line coverage measures whether each executable line of code was run at least once during testing. Branch coverage goes further — it checks whether each conditional branch (true/false paths in `if`, `else`, `switch` statements) was exercised. A line containing `if (x > 0)` could have 100% line coverage while only the `true` branch is tested. Branch coverage catches this, making it a stricter and more meaningful metric.

### Can I use one coverage reporting tool for multiple programming languages?

Yes. SonarQube Community Edition accepts coverage data from JaCoCo (Java), Coverage.py (Python, via Cobertura XML), Istanbul/nyc (JavaScript, via lcov), and many others. This makes it a unified self-hosted dashboard for polyglot projects. Alternatively, Grafana + Prometheus can display coverage from any tool that can output to a structured format.

### How do I combine coverage reports from multiple CI runners?

For Python, run `coverage run --parallel-mode` on each runner, then `coverage combine` to merge. For JavaScript/nyc, all runners write to the same `.nyc_output` directory (shared via CI artifact storage), and `nyc report` merges automatically. For Java/JaCoCo, use the `jacoco:merge` Maven goal or Gradle's JacocoMerge task to aggregate `.exec` files from parallel test suites.

### Should I aim for 100% code coverage?

No. 100% coverage is rarely practical and often counterproductive. It encourages writing tests that assert trivial code (getters, setters, boilerplate) rather than meaningful behavior. A realistic target is 80-90% for application code, with critical modules (authentication, financial calculations, data validation) pushed higher. Focus on testing behavior, not metrics.

### How do I exclude files from coverage calculations?

Each tool has its own exclusion syntax. For Coverage.py, use `omit = ["tests/*", "*/migrations/*"]` in `pyproject.toml`. For nyc, set `exclude: ['**/*.test.js', '**/__mocks__/**']` in the config. For JaCoCo, configure `<excludes>` in the Maven plugin or use `**/*Test*` patterns. Always exclude test files themselves, generated code, and third-party dependencies.

### Is self-hosted coverage better than using Codecov or Coveralls?

It depends on your priorities. Self-hosted solutions offer complete data control, no per-repo pricing, unlimited retention, and offline operation. SaaS platforms offer zero-infrastructure setup, pull request annotations, and polished UIs out of the box. For organizations handling sensitive code, operating in restricted networks, or managing dozens of repositories, self-hosted coverage typically provides better value and compliance.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "JaCoCo vs Coverage.py vs Istanbul/nyc: Self-Hosted Code Coverage Guide 2026",
  "description": "Compare JaCoCo, Coverage.py, and Istanbul/nyc for self-hosted code coverage. Learn how to collect, aggregate, and visualize coverage reports without relying on SaaS services like Codecov or Coveralls.",
  "datePublished": "2026-04-21",
  "dateModified": "2026-04-21",
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
