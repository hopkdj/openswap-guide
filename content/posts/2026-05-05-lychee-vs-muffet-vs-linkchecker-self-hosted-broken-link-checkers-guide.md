---
title: "Lychee vs Muffet vs LinkChecker: Best Self-Hosted Broken Link Checkers 2026"
date: 2026-05-05
tags: ["comparison", "guide", "self-hosted", "link-checker", "web-tools", "devops", "site-maintenance"]
draft: false
description: "Compare the top three self-hosted broken link checkers — lychee, muffet, and LinkChecker — for finding dead links across websites, documentation, and markdown projects. Docker deployment guides included."
---

A broken link on your website is more than a dead end — it erodes trust, hurts search rankings, and signals neglect to visitors and crawlers alike. Whether you manage a documentation site, a corporate blog, or a large e-commerce platform, automated link checking should be part of your regular maintenance workflow. Running it as a self-hosted service keeps your site inventory private, integrates with your CI/CD pipeline, and costs nothing beyond the compute you already have.

In this guide, we compare three leading open-source link checkers: **lychee** (a fast Rust-based checker), **muffet** (a Go-powered website crawler), and **LinkChecker** (a mature Python-based solution with comprehensive reporting). Each takes a different approach to link validation, and the right choice depends on whether you prioritize speed, breadth of coverage, or detailed reporting.

## Quick Comparison

| Feature | lychee | muffet | LinkChecker |
|---------|--------|--------|-------------|
| **Language** | Rust | Go | Python |
| **GitHub Stars** | 3,500+ | 2,500+ | 1,000+ |
| **Input Sources** | URLs, files, directories | Website URL | Website URL |
| **Markdown Support** | ✅ Native | ❌ | ❌ |
| **Concurrency** | Async streams | Goroutines | Threads |
| **Output Formats** | JSON, compact, detailed | Plain text, JSON | HTML, CSV, SQL, XML |
| **Rate Limiting** | ✅ Configurable | ✅ Built-in | ✅ Configurable |
| **Cookie/Auth Support** | ✅ | ✅ | ✅ |
| **Docker Image** | ✅ Official | ✅ Official | ✅ Community |
| **CI/CD Integration** | GitHub Action, CLI | CLI | CLI |
| **Last Updated** | May 2026 | May 2026 | March 2026 |

## lychee — Fast Rust-Based Link Checker

lychee is an async, stream-based link checker written in Rust. It finds broken URLs and email addresses inside Markdown, HTML, reStructuredText, plain text files, and live websites. Its parallel execution model makes it one of the fastest link checkers available.

**Key strengths:**

- **Native Markdown support** — parses Markdown files directly, extracting links from inline syntax, reference-style links, and image tags without needing a rendering step
- **Flexible input** — accepts URLs, file paths, directory globs, and stdin piped content
- **Multiple output formats** — compact for CI, JSON for parsing, detailed for debugging
- **GitHub Action** — official `lycheeverse/lychee-action` for CI integration
- **Remap rules** — rewrite URLs on the fly for staging environments
- **Exclude patterns** — skip specific domains, paths, or regex patterns

**Limitations:**

- No web crawling — checks only links found in provided input, doesn't discover pages
- No HTML report generation (JSON is the richest output)

### Install lychee

```bash
# macOS (Homebrew)
brew install lychee

# Rust (cargo)
cargo install lychee

# Linux (binary)
curl -sSfL https://github.com/lycheeverse/lychee/releases/latest/download/lychee-x86_64-unknown-linux-gnu.tar.gz | tar xz
sudo mv lychee /usr/local/bin/
```

### Docker Compose for lychee

lychee is typically run as a one-shot CLI container, but you can schedule it via cron or CI:

```yaml
version: "3.8"
services:
  lychee-check:
    image: ghcr.io/lycheeverse/lychee:latest
    volumes:
      - ./site:/site:ro
    command: ["/site/**/*.md", "--format", "json", "--output", "/tmp/lychee-results.json"]
    restart: "no"
```

### Example: Check a documentation site

```bash
# Check all markdown files in a project
lychee docs/**/*.md --verbose --exclude "localhost|staging.example.com"

# Check a live website with rate limiting
lychee https://example.com --max-concurrency 5 --max-retries 3 --timeout 20

# CI-friendly compact output
lychee --format compact *.md && echo "All links OK"
```

## muffet — Go-Powered Website Crawler

muffet is a fast website link checker written in Go. Unlike lychee, muffet crawls entire websites by following links recursively, validating every URL it discovers along the way. It uses goroutines for high concurrency and is designed for checking live production sites.

**Key strengths:**

- **Recursive crawling** — follows links from page to page, building a complete map of broken URLs across an entire domain
- **Color-coded output** — terminal output with colored status codes for quick visual scanning
- **Buffered HTTP client** — handles thousands of concurrent requests efficiently
- **Ignore patterns** — skip specific URL patterns with regex
- **Multiple schemes** — supports HTTP, HTTPS, and mailto links
- **Single binary** — no runtime dependencies, easy to deploy

**Limitations:**

- No Markdown or file input — only crawls live URLs
- Less output format flexibility (primarily terminal output)

### Install muffet

```bash
# Go install
go install github.com/raviqqe/muffet/v2@latest

# macOS (Homebrew)
brew install muffet

# Debian/Ubuntu (.deb)
curl -sSfL https://github.com/raviqqe/muffet/releases/latest/download/muffet_linux_amd64.deb -o muffet.deb
sudo dpkg -i muffet.deb
```

### Docker Compose for muffet

```yaml
version: "3.8"
services:
  muffet-check:
    image: ghcr.io/raviqqe/muffet:latest
    entrypoint: ["muffet"]
    command: ["--buffer-size=1000", "--max-connections=50", "https://example.com"]
    restart: "no"
```

### Example: Crawl a production site

```bash
# Quick scan of a website
muffet https://example.com

# Crawling with custom concurrency and timeout
muffet --max-connections=20 --timeout=30 --buffer-size=2000 https://docs.example.com

# Ignore specific paths (login pages, CDNs)
muffet --exclude='(login|cdn\.|/api/v1)' https://example.com
```

## LinkChecker — Mature Python Solution

LinkChecker is one of the oldest and most comprehensive link checking tools available. Written in Python, it validates links in websites and HTML documents with extensive output options including HTML reports, CSV exports, and SQL database storage.

**Key strengths:**

- **Rich reporting** — generates HTML reports with clickable link maps, CSV for spreadsheets, and SQL for database storage
- **Deep checking** — validates HTML syntax, checks SSL certificates, follows redirects, and verifies anchors
- **Authentication support** — handles HTTP auth, cookies, and login forms for protected content
- **Plugin system** — extensible via Python plugins for custom checks
- **Recursive with depth control** — configurable crawl depth for large sites
- **Cache support** — caches HTTP responses to speed up repeated checks

**Limitations:**

- Slower than Rust/Go alternatives due to Python runtime
- Requires Python 3.x environment
- Less active development compared to lychee and muffet

### Install LinkChecker

```bash
# pip
pip3 install linkchecker

# Debian/Ubuntu
sudo apt install linkchecker

# From source
git clone https://github.com/linkchecker/linkchecker.git
cd linkchecker
pip3 install -e .
```

### Docker Compose for LinkChecker

```yaml
version: "3.8"
services:
  linkchecker:
    image: linkchecker/linkchecker:latest
    volumes:
      - ./reports:/reports
    command: ["--output=html", "--file=/reports/report.html", "https://example.com"]
    restart: "no"
```

### Example: Generate a full report

```bash
# HTML report for a website
linkchecker --output=html --file=report.html https://example.com

# CSV export for analysis
linkchecker --output=csv --file=broken-links.csv https://docs.example.com

# Check with authentication
linkchecker --login=admin --password=secret --check-extern https://internal.example.com

# Limit crawl depth and threads
linkchecker --max-depth=5 --threads=10 https://example.com
```

## Choosing the Right Tool

| Use Case | Recommended Tool | Why |
|----------|-----------------|-----|
| **Documentation site (Markdown)** | lychee | Native Markdown parsing, file input, GitHub Action |
| **Full website crawl** | muffet | Recursive crawling, fast Go concurrency |
| **Detailed HTML reports** | LinkChecker | Rich output formats, HTML report generation |
| **CI/CD pipeline integration** | lychee | Official GitHub Action, compact output mode |
| **Large site with auth** | LinkChecker | Login form support, cookie handling |
| **Quick ad-hoc check** | muffet | Single binary, zero configuration |
| **Scheduled monitoring** | Any — Docker | All three run in containers, schedule with cron |

## Why Run Broken Link Checking Self-Hosted?

Running link checkers on your own infrastructure offers several advantages over SaaS alternatives:

**Privacy:** Your complete site map and URL inventory never leave your network. For internal documentation, staging environments, or sites behind authentication, self-hosting is the only viable option. SaaS link checkers need public access to every URL they validate.

**Cost:** All three tools are free and open-source. At scale, SaaS link monitoring services charge per-page or per-site fees that quickly exceed the cost of a small VM. Self-hosted checkers cost nothing beyond compute you already own.

**CI/CD Integration:** Running link checkers as part of your build pipeline catches broken links before they reach production. lychee's official GitHub Action makes this trivial — add it to your PR workflow and block merges when broken links are detected. For more complex pipelines, muffet and LinkChecker run equally well in any CI environment.

**Customization:** Self-hosted tools let you configure exclusion rules, authentication, rate limits, and output formats to match your exact needs. You control the check frequency, the scope of validation, and how results are reported and acted upon.

For teams already running self-hosted monitoring infrastructure, pairing link checking with [synthetic monitoring tools](../2026-04-28-gatus-vs-k6-vs-uptime-kuma-self-hosted-synthetic-monitoring/) gives you comprehensive site health coverage — both availability and content integrity. If you also manage [web performance benchmarks](../2026-04-21-sitespeedio-vs-webpagetest-vs-lighthouse-self-hosted-web-performance-monitoring-2026/), adding link validation rounds out your quality assurance pipeline.

## FAQ

### What is the difference between lychee, muffet, and LinkChecker?

lychee checks links in local files (Markdown, HTML, text) and individual URLs using Rust async streams. muffet crawls entire websites recursively using Go goroutines, following every link it discovers. LinkChecker is a Python-based tool that combines crawling with rich reporting — it generates HTML, CSV, and SQL output formats for analysis and compliance.

### Can I run these tools in a CI/CD pipeline?

Yes. lychee has an official GitHub Action (`lycheeverse/lychee-action`) that checks links on every PR. muffet and LinkChecker can run in any CI environment as CLI commands — add them to your `.github/workflows/`, GitLab CI, or Jenkins pipeline. All three have Docker images for containerized CI runners.

### How do I exclude certain URLs from being checked?

All three tools support exclusion patterns. lychee uses `--exclude` with regex. muffet uses `--exclude` with regex as well. LinkChecker uses `--ignore-url` with regex patterns. Common exclusions include localhost URLs, staging environments, external CDNs, and login pages.

### Do these tools check email addresses?

lychee checks `mailto:` links in addition to HTTP/HTTPS URLs. muffet also validates mailto links during crawling. LinkChecker checks email addresses but does not verify whether the mailbox actually exists — it only validates the format.

### How fast are these tools on large sites?

lychee can process thousands of links per second on local files thanks to Rust's async runtime. muffet handles hundreds of concurrent HTTP requests using Go goroutines — a 1,000-page site typically checks in under 30 seconds. LinkChecker is slower due to Python's threading model but compensates with caching for repeated runs.

### Can I schedule automatic link checking?

Yes. The recommended approach is to run each tool via Docker Compose as a one-shot service scheduled with cron, or integrate into your CI/CD pipeline for checks on every deploy. For example, a nightly cron job running `docker compose run lychee-check` will email or Slack you the results.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Lychee vs Muffet vs LinkChecker: Best Self-Hosted Broken Link Checkers 2026",
  "description": "Compare the top three self-hosted broken link checkers — lychee, muffet, and LinkChecker — for finding dead links across websites, documentation, and markdown projects.",
  "datePublished": "2026-05-05",
  "dateModified": "2026-05-05",
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
