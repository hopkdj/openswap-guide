---
title: "Pa11y vs Lighthouse CI vs axe-core: Best Self-Hosted Accessibility Testing 2026"
date: 2026-04-18
tags: ["comparison", "guide", "self-hosted", "testing", "accessibility", "ci-cd"]
draft: false
description: "Compare Pa11y, Lighthouse CI, and axe-core for self-hosted automated web accessibility testing. Docker configs, CI/CD integration, and WCAG compliance guides."
---

Web accessibility is no longer optional. With the European Accessibility Act taking effect in 2025 and lawsuits increasing worldwide, every public-facing website must meet WCAG 2.2 AA standards. Automated accessibility testing catches 30-50% of compliance issues before they reach production — but commercial platforms like Siteimprove and Deque University charge hundreds of dollars per month.

This guide covers three powerful open-source tools you can self-host for free: **Pa11y**, **Lighthouse CI**, and **axe-core**. We'll compare features, show [docker](https://www.docker.com/) Compose configurations, and walk through CI/CD pipeline integration so you can run accessibility audits on every commit without sending data to third-party services.

## Why Self-Host Accessibility Testing

Running accessibility tests on your own infrastructure offers several advantages over SaaS alternatives:

- **Privacy**: Your URLs and page content never leave your network. Critical for internal dashboards, staging environments, and sensitive applications.
- **Unlimited scans**: No per-page or per-month quotas. Run audits on every build, every branch, every URL.
- **Custom baselines**: Set accessibility budgets that match your project's compliance targets (WCAG A, AA, or AAA).
- **CI/CD integration**: Gate merges on accessibility scores. Fail builds when new violations are introduced.
- **Zero cost**: All three tools are open-source with no licensing fees.

For related reading, see our [self-hosted CI/CD platform guide](../self-hosted-ci-cd-woodpecker-drone-jenkins-concourse-2026/) for setting up the pipeline infrastructure, and our [E2E testing tools comparison](../self-hosted-e2e-testing-tools-playwright-cypress-selenium-guide-2026/) which covers complementary testing approaches.

## Tool Overview

### Pa11y (4,425 GitHub Stars)

Pa11y is a command-line accessibility testing tool maintained by the accessibility consultancy [Springload](https://github.com/pa11y/pa11y). It wraps the axe-core engine and provides a simple CLI for running audits against any URL. The project was last updated in April 2026 and is written in JavaScript.

**Key strengths**:
- Dead-simple CLI interface — one command to audit any URL
- Built-in WCAG 2.0, 2.1, and 2.2 standard support
- HTML, JSON, CSV, and TSV output formats
- Dashboard web UI via the separate `pa11y-dashboard` project
- Scheduled monitoring with `pa11y-webservice`

Pa11y is ideal for teams that want quick, reliable accessibility audits without com[plex](https://www.plex.tv/) setup. Its CLI-first design makes it easy to integrate into shell scripts, cron jobs, and CI pipelines.

### Lighthouse CI (30,067 GitHub Stars)

Lighthouse CI brings Google's Lighthouse engine — the same tool used in Chrome DevTools — into automated CI/CD workflows. Maintained by Google under the [ChromeLabs organization](https://github.com/GoogleChrome/lighthouse), it is the most actively developed project in this comparison with 30,000+ stars and daily commits.

**Key strengths**:
- Comprehensive audits: accessibility, performance, SEO, PWA, and best practices
- Score tracking over time with the Lighthouse CI Server
- GitHub integration with pull request comments and status checks
- Budget assertions that fail CI when scores drop below thresholds
- HTML report generation with detailed remediation guidance

Lighthouse CI is the best choice for teams already invested in the Google ecosystem who want accessibility testing alongside performance and SEO audits in a single tool.

### axe-core (7,050 GitHub Stars)

axe-core, developed by [Deque Systems](https://github.com/dequelabs/axe-core), is the accessibility testing engine that powers Pa11y, Chrome DevTools, and many commercial platforms. It is the industry-standard open-source accessibility engine, written in JavaScript and used by over 50,000 projects worldwide. Last updated in April 2026.

**Key strengths**:
- The most accurate accessibility engine available (fewer false positives/negatives)
- Can be embedded directly into JavaScript test suites (Jest, Cypress, Playwright)
- Supports WCAG 2.0, 2.1, 2.2, and Section 508 standards
- Fine-grained rule configuration — enable/disable individual checks
- Integration libraries for every major test framework

axe-core is the engine of choice when you need accessibility testing embedded directly into your existing test infrastructure rather than running as a separate process.

## Feature Comparison

| Feature | Pa11y | Lighthouse CI | axe-core |
|---------|-------|---------------|----------|
| **License** | LGPL-3.0 | Apache-2.0 | MPL-2.0 |
| **GitHub Stars** | 4,425 | 30,067 | 7,050 |
| **Language** | JavaScript | JavaScript | JavaScript |
| **CLI Interface** | ✅ Native | ✅ Via `lhci` | ❌ Library only |
| **Web Dashboard** | ✅ pa11y-dashboard | ✅ LHCI Server | ❌ |
| **WCAG 2.2 Support** | ✅ | ✅ | ✅ |
| **Performance Audits** | ❌ | ✅ | ❌ |
| **SEO Audits** | ❌ | ✅ | ❌ |
| **Embedded in Tests** | ❌ | ❌ | ✅ |
| **CI Budget Gates** | ✅ (exit codes) | ✅ (assertions) | ✅ (custom logic) |
| **Docker Support** | ✅ | ✅ | ✅ |
| **Scheduled Monitoring** | ✅ pa11y-webservice | ✅ cron mode | ❌ |
| **GitHub PR Comments** | ❌ | ✅ | ❌ |
| **Report Formats** | HTML, JSON, CSV, TSV | HTML, JSON | JSON |

## Installing with Docker Compose

### Pa11y with Dashboard

The Pa11y ecosystem consists of three components: the CLI tool, a webservice for scheduling, and a web dashboard for viewing results.

```yaml
# docker-compose.yml - Pa11y Stack
version: "3.8"

services:
  pa11y-webservice:
    image: pa11y/webservice:latest
    ports:
      - "3001:3001"
    environment:
      - NODE_ENV=production
      - PA11Y_WEB_SERVICE_DB=mongodb://mongo:27017/pa11y
    depends_on:
      - mongo

  mongo:
    image: mongo:7
    volumes:
      - pa11y-data:/data/db

  pa11y-dashboard:
    image: pa11y/dashboard:latest
    ports:
      - "3002:3002"
    environment:
      - PA11Y_WEBSERVICE_URL=http://pa11y-webservice:3001
    depends_on:
      - pa11y-webservice

volumes:
  pa11y-data:
```

Start the stack and schedule your first audit:

```bash
docker compose up -d

# Run a single audit via CLI
npx pa11y https://example.com --standard WCAG2AA --reporter html > report.html

# Or schedule recurring checks via the webservice API
curl -X POST http://localhost:3001/tasks \
  -H "Content-Type: application/json" \
  -d '{"name": "Homepage", "url": "https://example.com", "timeout": 30000}'
```

### Lighthouse CI Server

Lighthouse CI provides both a CLI for running audits and an optional server for persisting and comparing results over time.

```yaml
# docker-compose.yml - Lighthouse CI
version: "3.8"

services:
  lhci-server:
    image: patrickhulce/lhci-server:latest
    ports:
      - "9001:9001"
    environment:
      - LHCI_PORT=9001
    volumes:
      - lhci-data:/data

volumes:
  lhci-data:
```

Configure and run Lighthouse CI audits:

```bash
# Install the CLI globally
npm install -g @lhci/cli

# Initialize LHCI in your project
lhci autorun

# Or run against a specific URL
lhci collect --url=https://example.com
lhci upload --target=lhci-server --host=http://localhost:9001
```

Create a `lighthouserc.json` configuration file to set accessibility budgets:

```json
{
  "ci": {
    "collect": {
      "url": ["https://example.com/", "https://example.com/about", "https://example.com/contact"],
      "numberOfRuns": 3
    },
    "assert": {
      "assertions": {
        "categories:accessibility": ["error", {"minScore": 0.90}],
        "categories:performance": ["warn", {"minScore": 0.80}],
        "categories:seo": ["warn", {"minScore": 0.85}]
      }
    },
    "upload": {
      "target": "lhci-server",
      "serverBaseUrl": "http://localhost:9001"
    }
  }
}
```

### axe-core in Docker with Playwright

For embedding axe-core directly into a test suite, use a Node.js container with Playwright:

```yaml
# docker-compose.yml - axe-core + Playwright
version: "3.8"

services:
  axe-tests:
    build:
      context: .
      dockerfile: Dockerfile.axe
    volumes:
      - ./tests:/app/tests
      - ./reports:/app/reports
    [nginx](https://nginx.org/)ds_on:
      - web-app

  web-app:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./dist:/usr/share/nginx/html
```

```dockerfile
# Dockerfile.axe
FROM mcr.microsoft.com/playwright:v1.50.0-jammy

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
CMD ["npx", "playwright", "test"]
```

Example test file using axe-core with Playwright:

```javascript
// tests/accessibility.spec.js
import { test, expect } from '@playwright/test';
import { injectAxe, checkA11y, getViolations } from 'axe-playwright';

test.describe('Accessibility Audit', () => {
  test('homepage meets WCAG AA', async ({ page }) => {
    await page.goto('http://web-app:80');
    await injectAxe(page);
    const violations = await getViolations(page, null, {
      standard: 'WCAG2AA',
    });
    expect(violations.length).toBe(0);
    await checkA11y(page);
  });

  test('navigation is keyboard accessible', async ({ page }) => {
    await page.goto('http://web-app:80');
    await injectAxe(page);
    const { violations } = await checkA11y(page, 'nav', {
      detailedReport: true,
    });
    expect(violations).toEqual([]);
  });
});
```

## CI/CD Pipeline Integration

### GitHub Actions with Pa11y

```yaml
# .github/workflows/accessibility.yml
name: Accessibility Audit

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  pa11y-ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20

      - name: Install Pa11y CI
        run: npm install -g pa11y-ci

      - name: Start application
        run: docker compose up -d && sleep 10

      - name: Run accessibility audit
        run: |
          pa11y-ci --config .pa11yci.js --threshold 0
        env:
          BASE_URL: http://localhost:3000
```

```javascript
// .pa11yci.js
module.exports = {
  defaults: {
    standard: "WCAG2AA",
    runners: ["htmlcs", "axe"],
    chromeLaunchConfig: { args: ["--no-sandbox"] }
  },
  urls: [
    "http://localhost:3000/",
    "http://localhost:3000/about",
    "http://localhost:3000/contact",
    "http://localhost:3000/pricing"
  ],
  thresholds: {
    error: 0,
    warning: 10
  }
};
```

### GitHub Actions with Lighthouse CI

```yaml
# .github/workflows/lighthouse.yml
name: Lighthouse CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lighthouse:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20

      - name: Install LHCI
        run: npm install -g @lhci/cli

      - name: Build
        run: npm run build

      - name: Serve and Audit
        run: lhci autorun
        env:
          LHCI_GITHUB_APP_TOKEN: ${{ secrets.LHCI_GITHUB_APP_TOKEN }}

      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: lighthouse-reports
          path: .lighthouseci/
```

## Choosing the Right Tool

Your choice depends on where accessibility testing fits in your workflow:

**Choose Pa11y if:**
- You need simple CLI-based audits with scheduled monitoring
- You want a self-hosted web dashboard for tracking violations over time
- Your team prefers a focused accessibility-only tool

**Choose Lighthouse CI if:**
- You want accessibility alongside performance, SEO, and PWA audits
- You need GitHub pull request integration with automatic comments
- You want to track score trends over time with a centralized server

**Choose axe-core if:**
- You want to embed accessibility checks into existing JavaScript test suites
- You need fine-grained control over which WCAG rules are enforced
- You are already using Playwright, Cypress, or Jest and want native integration

For a complete quality pipeline, consider combining axe-core embedded tests (fast, per-component) with Lighthouse CI audits (comprehensive, per-page) — a pattern similar to what we cover in our [code quality tools comparison](../sonarqube-vs-semgrep-vs-codeql-self-hosted-code-quality-guide-2026/).

## FAQ

### What is the difference between Pa11y and axe-core?

Pa11y is a command-line tool that uses axe-core as its underlying engine under the hood. Pa11y provides a convenient CLI wrapper, output formatting, and scheduling capabilities. axe-core is the raw JavaScript library that performs the actual accessibility analysis. Many teams use Pa11y for quick audits and axe-core when embedding checks into custom test frameworks.

### Can these tools catch all accessibility issues?

No. Automated tools typically catch 30-50% of WCAG violations. Issues like logical reading order, meaningful alt text quality, keyboard navigation flow, and color contrast in context still require manual testing. Always supplement automated scans with manual testing using screen readers like NVDA or VoiceOver.

### Which WCAG standard should I target?

For most organizations, **WCAG 2.1 AA** is the legal baseline and the recommended target. WCAG 2.2 AA adds updated criteria for mobile accessibility and cognitive disabilities. WCAG AAA is the highest level but may not be achievable for all content types. Start with AA and incrementally work toward AAA for critical user flows.

### How do I set up accessibility budgets in CI?

Accessibility budgets define the minimum acceptable accessibility score and maximum allowed violations. In Lighthouse CI, use the `assert` configuration in `lighthouserc.json` to set `categories:accessibility` to a minimum score (e.g., 0.90). In Pa11y CI, use the `thresholds` property in `.pa11yci.js` to set maximum error and warning counts. Both tools will exit with a non-zero code when budgets are violated, failing your CI build.

### Is Lighthouse CI free for self-hosted use?

Yes. Lighthouse CI and the Lighthouse CI Server are completely open-source under the Apache 2.0 license. The `lhci-server` Docker image is free to self-host. Google also offers a free public Lighthouse CI server with limited storage, but self-hosting gives you unlimited storage, data privacy, and full control over retention policies.

### How often should I run accessibility audits?

Run automated accessibility audits on every commit as part of your CI pipeline. For production monitoring, schedule weekly full-site scans to catch regressions introduced by content updates or dependency changes. Pa11y's webservice component is designed specifically for this scheduled monitoring pattern, while Lighthouse CI focuses on per-commit validation.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Pa11y vs Lighthouse CI vs axe-core: Best Self-Hosted Accessibility Testing 2026",
  "description": "Compare Pa11y, Lighthouse CI, and axe-core for self-hosted automated web accessibility testing. Docker configs, CI/CD integration, and WCAG compliance guides.",
  "datePublished": "2026-04-18",
  "dateModified": "2026-04-18",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>
