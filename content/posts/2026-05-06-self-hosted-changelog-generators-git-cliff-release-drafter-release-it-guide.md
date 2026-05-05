---
title: "Self-Hosted Release Notes & Changelog Tools: git-cliff vs Release-Drafter vs release-it (2026)"
date: 2026-05-06
tags: ["comparison", "guide", "self-hosted", "devops", "release-management", "changelog"]
draft: false
---

Automating release notes and changelog generation is essential for maintaining clean, professional project histories. Instead of manually writing release summaries, self-hosted changelog tools parse git commits, pull requests, and tags to produce structured, readable release notes — all without relying on SaaS platforms.

In this guide, we compare three popular self-hosted solutions for generating release notes and changelogs: **git-cliff**, **GitHub Release Drafter**, and **release-it**. Each takes a different approach — from convention-driven parsing to PR-based drafting to full release automation — and each runs entirely on your own infrastructure.

## What Are Self-Hosted Changelog Generators?

Changelog generators automate the process of compiling commit history into human-readable release notes. They parse git log output, categorize changes by type (features, fixes, breaking changes), and format them into Markdown or other output formats.

Key benefits of self-hosted changelog tools include:

- **No SaaS dependency**: Generate release notes without external services or API keys
- **Full control**: Customize formatting, categories, and filtering rules to match your workflow
- **CI/CD integration**: Embed changelog generation directly into your build pipeline
- **Privacy-sensitive repos**: Keep commit history and release notes within your own infrastructure
- **Offline capability**: Generate changelogs without internet access

For teams managing multiple repositories, automated changelog generation saves hours per release cycle while maintaining consistent formatting and comprehensive coverage.

## git-cliff vs Release-Drafter vs release-it: Feature Comparison

| Feature | git-cliff | Release Drafter | release-it |
|---------|-----------|-----------------|------------|
| **Type** | CLI changelog generator | GitHub Action | Release automation CLI |
| **Language** | Rust | JavaScript/TypeScript | JavaScript/TypeScript |
| **Stars** | 8,500+ | 3,800+ | 8,900+ |
| **Conventional Commits** | Full support | Via config | Full support |
| **Semver Bumping** | Automatic | Via labels | Automatic |
| **GitHub Integration** | Optional | Native | Full |
| **GitLab Integration** | Yes | No | Yes |
| **npm Integration** | No | No | Full |
| **Custom Templates** | Handlebars | Template editor | Template engine |
| **Breaking Changes Detection** | Regex-based | Label-based | Regex-based |
| **Self-Hosted** | Yes | GitHub Actions runner | Yes |
| **Docker Support** | Official image | N/A | Yes |

## git-cliff: Convention-Driven Changelog Generation

[git-cliff](https://github.com/orhun/git-cliff) is a Rust-based changelog generator that parses git commits following Conventional Commits or customizable regex patterns. It produces beautifully formatted release notes using Handlebars templates.

**Key features:**
- Blazing fast performance thanks to Rust
- Supports conventional commits (feat, fix, chore, etc.)
- Custom regex patterns for any commit message format
- Handlebars templating for full output control
- Can output to stdout, file, or GitHub release notes
- Supports git tags for versioned changelog segments

### Installing git-cliff

```bash
# Via cargo
cargo install git-cliff

# Via Homebrew (macOS/Linux)
brew install git-cliff

# Via Docker
docker run --rm -v "$(pwd):/app" -w /app ghcr.io/orhun/git-cliff:latest --help
```

### Docker Compose for CI/CD

```yaml
version: "3.8"
services:
  changelog:
    image: ghcr.io/orhun/git-cliff:latest
    container_name: git-cliff
    volumes:
      - .:/repo
      - ./cliff.toml:/app/cliff.toml:ro
    working_dir: /repo
    command: git-cliff --config /app/cliff.toml --output CHANGELOG.md
    restart: "no"
```

### Sample cliff.toml Configuration

```toml
[changelog]
header = """
# Changelog

All notable changes to this project will be documented in this file.
"""
body = """
{% if version %}
    ## [{{ version }}] - {{ timestamp }}
{% else %}
    ## [Unreleased]
{% endif %}
{% for group, commits in commits | group_by(attribute="group") %}
    ### {{ group | upper_first }}
    {% for commit in commits %}
        - {{ commit.message | upper_first }}
    {% endfor %}
{% endfor %}
"""

[git]
conventional_commits = true
filter_unconventional = true
commit_parsers = [
    { message = "^feat", group = "Features" },
    { message = "^fix", group = "Bug Fixes" },
    { message = "^perf", group = "Performance" },
    { message = "^doc", group = "Documentation" },
    { message = "^refactor", group = "Refactoring" },
    { message = "^test", group = "Tests" },
]
```

## GitHub Release Drafter: PR-Based Release Notes

[Release Drafter](https://github.com/release-drafter/release-drafter) is a GitHub Action that automatically drafts release notes as pull requests are merged. It categorizes PRs by label and produces clean, structured release summaries.

**Key features:**
- Native GitHub integration via Actions
- Label-based categorization (feature, bug, maintenance)
- Automatic version bumping based on PR labels
- Customizable Markdown templates
- Runs on self-hosted GitHub Actions runners
- Supports prerelease drafting

### GitHub Actions Workflow

```yaml
name: Release Drafter

on:
  push:
    branches:
      - main

permissions:
  contents: read

jobs:
  update_release_draft:
    permissions:
      contents: write
      pull-requests: read
    runs-on: self-hosted
    steps:
      - uses: release-drafter/release-drafter@v6
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Release Drafter Configuration

```yaml
name-template: "v$RESOLVED_VERSION"
tag-template: "v$RESOLVED_VERSION"
categories:
  - title: "Features"
    labels: ["feature", "enhancement"]
  - title: "Bug Fixes"
    labels: ["fix", "bugfix", "bug"]
  - title: "Maintenance"
    labels: ["chore", "maintenance", "ci"]
change-template: "- $TITLE (#$NUMBER) by @$AUTHOR"
version-resolver:
  major:
    labels: ["major"]
  minor:
    labels: ["minor", "feature"]
  patch:
    labels: ["patch", "fix", "bug"]
  default: patch
template: |
  ## Changes

  $CHANGES

  ## Contributors

  $CONTRIBUTORS
```

## release-it: Full Release Automation

[release-it](https://github.com/release-it/release-it) goes beyond changelog generation — it handles the entire release workflow including version bumping, changelog generation, git tagging, pushing, and publishing to npm, GitHub Releases, or GitLab.

**Key features:**
- End-to-end release automation
- Supports npm, GitHub, GitLab, and custom plugins
- Interactive or non-interactive modes
- Pre-release and dry-run support
- Custom hooks for pre/post release steps
- Monorepo support

### Installing release-it

```bash
# Via npm
npm install --save-dev release-it

# Via Docker
docker run --rm -v "$(pwd):/app" -w /app ghcr.io/release-it/release-it:latest --dry-run
```

### Docker Compose for Automated Releases

```yaml
version: "3.8"
services:
  release:
    image: ghcr.io/release-it/release-it:latest
    container_name: release-it
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - NPM_TOKEN=${NPM_TOKEN}
    volumes:
      - .:/app
      - ./.release-it.json:/app/.release-it.json:ro
    working_dir: /app
    command: release-it --ci --config /app/.release-it.json
    restart: "no"
```

### Configuration (.release-it.json)

```json
{
  "git": {
    "commitMessage": "chore: release v${version}",
    "tagName": "v${version}",
    "push": true
  },
  "github": {
    "release": true,
    "releaseName": "v${version}",
    "autoGenerate": true
  },
  "npm": {
    "publish": false
  },
  "hooks": {
    "before:init": ["npm test", "npm run lint"],
    "after:bump": "npm run build",
    "after:release": "echo Successfully released v${version}!"
  }
}
```

## Choosing the Right Tool

**Use git-cliff when:**
- You want fast, lightweight changelog generation
- Your team follows Conventional Commits
- You need full template customization with Handlebars
- You work across multiple git platforms (GitHub, GitLab, Gitea)

**Use Release Drafter when:**
- You are on GitHub and want PR-based release notes
- Your team uses labels for PR categorization
- You want automatic version bumping based on merged PRs
- You prefer minimal configuration

**Use release-it when:**
- You need end-to-end release automation, not just changelogs
- You publish to npm, GitHub Releases, or both
- You want interactive release prompts for human review
- You need custom hooks for build/test steps

## Why Self-Host Your Changelog Generation?

Generating release notes on your own infrastructure offers several advantages over SaaS changelog services:

**Data privacy and security**: Commit histories often contain sensitive information about internal processes, feature roadmaps, and bug patterns. Self-hosted tools keep this data within your infrastructure, avoiding exposure to third-party changelog SaaS platforms.

**CI/CD pipeline integration**: Self-hosted changelog generators integrate seamlessly with existing CI/CD pipelines running on self-hosted runners. No external API calls mean faster builds and no rate limit concerns.

**Customization flexibility**: Open-source changelog tools allow unlimited customization of output format, categorization rules, and template structure. SaaS services often lock you into predefined formats and limited configuration options.

**No vendor lock-in**: When changelog generation is part of your CI/CD pipeline rather than a SaaS dependency, you can switch git platforms or CI providers without losing your release history or formatting.

**Cost efficiency**: All three tools compared here are free and open-source. For teams managing dozens of repositories, avoiding per-repository SaaS pricing for release management adds up quickly.

For teams also managing [database migrations](../bytebase-vs-flyway-vs-liquibase-self-hosted-database-migration-guide-2026/), automating changelog generation complements automated database versioning. Similarly, [self-hosted Ansible UI tools](../semaphore-vs-awx-vs-rundeck-self-hosted-ansible-ui-guide-2026/) benefit from clean release notes to track infrastructure changes.

## FAQ

### What is the difference between git-cliff and Release Drafter?

git-cliff is a standalone CLI tool that parses git commit history to generate changelogs, while Release Drafter is a GitHub Action that drafts release notes based on merged pull requests and their labels. git-cliff works with any git repository on any platform; Release Drafter requires GitHub.

### Can I use git-cliff without Conventional Commits?

Yes. git-cliff supports custom regex patterns for parsing commit messages. You can define your own commit_parsers in the cliff.toml configuration to match any commit message format your team uses.

### Does release-it work with GitLab?

Yes. release-it has built-in support for both GitHub and GitLab releases. Configure the gitlab section in your .release-it.json file to publish releases to your self-hosted GitLab instance.

### How do I run these tools on self-hosted CI runners?

All three tools run as standard CLI commands or Docker containers. For GitHub Actions, use the official actions or Docker images on self-hosted runners. For GitLab CI, add the commands to your .gitlab-ci.yml pipeline stages.

### Can these tools generate changelogs for monorepos?

release-it has explicit monorepo support via plugins. git-cliff can generate changelogs for specific paths or packages using its configuration options. Release Drafter works per-repository, so monorepo support requires separate configurations per package.

### Do these tools support semantic versioning?

All three tools support semver. git-cliff can bump versions based on commit types (feat = minor, fix = patch, breaking = major). Release Drafter resolves versions from PR labels. release-it supports interactive or automatic semver bumping.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Release Notes and Changelog Tools: git-cliff vs Release-Drafter vs release-it (2026)",
  "description": "Compare self-hosted changelog generators - git-cliff, GitHub Release Drafter, and release-it - with Docker Compose configs and Conventional Commits integration.",
  "datePublished": "2026-05-06",
  "dateModified": "2026-05-06",
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
