---
title: "Self-Hosted Merge Queue & PR Gating Bots: Bors-ng vs Kodiak vs Homu Compared 2026"
date: "2026-06-17"
tags: ["merge-queue", "ci-cd", "code-review", "git", "automation", "developer-tools", "docker", "self-hosted"]
draft: false
---

## Why Self-Host a Merge Queue Bot?

Modern development teams use merge queues to protect their main branch from broken builds. Instead of merging PRs immediately after approval, a merge queue bot serializes merges, tests each one against the latest main, and only merges if all checks pass. This eliminates "merge skew" — the scenario where two PRs pass CI independently but break when merged together.

Self-hosting your merge queue bot gives you full control over the gating logic, keeps your repository data private, and avoids vendor lock-in. Unlike SaaS solutions (Mergify, Graphite, Trunk Merge), self-hosted bots run on your own infrastructure with zero per-seat costs and no external API dependency.

For a deep dive into the code review process itself, see our [self-hosted code review platforms guide](../gerrit-vs-review-board-vs-phorge-self-hosted-code-review-guide/). If you are building out your CI pipeline, our [self-hosted CI/CD agents comparison](../github-actions-runner-vs-gitlab-runner-vs-woodpecker-self-hosted-ci-agents-2026/) covers runner deployment.

## Comparison Table: Merge Queue Bots at a Glance

| Feature | Bors-ng | Kodiak | Homu |
|---------|---------|--------|------|
| **Language** | Elixir | Python | Python |
| **Stars** | 1,531 | 1,102 | 213 |
| **Deployment** | Docker, Heroku | Docker | Docker |
| **GitHub Support** | ✅ Full | ✅ Full | ✅ Full |
| **GitLab Support** | ❌ | ❌ | ❌ |
| **Merge Strategy** | Not Rocket Science Rule | Auto-update + merge | Not Rocket Science Rule |
| **Batch Testing** | ✅ Merges batched PRs together | ❌ Serial only | ✅ `rollup` mode |
| **Web Dashboard** | ✅ | ❌ (GitHub Checks) | ✅ |
| **Priority Labels** | ✅ | ✅ | ✅ |
| **Approval Requirements** | ✅ Configurable | ✅ | ✅ |
| **Last Updated** | Apr 2024 | May 2026 | Nov 2025 |
| **License** | Apache 2.0 | MIT | Apache 2.0 |

## What Is "Not Rocket Science Rule" Merging?

All three bots implement some form of the **Not Rocket Science Rule** (NRSR), a merge strategy popularized by the Rust community. The rule is simple: a PR can only be merged if it passes CI after being rebased onto the latest main branch — never based on an outdated base.

This prevents the classic failure mode where two developers both pass CI on their feature branches, merge one, and the second PR silently breaks the build. The merge bot acts as a serialization point, ensuring every merge candidate is tested against the exact state of main at merge time.

## Bors-ng: The Rust-Inspired Merge Bot

Bors-ng is the most widely adopted self-hosted merge bot, originally inspired by the Rust project's Homu bot. Written in Elixir, it runs on the BEAM virtual machine with excellent concurrency and fault tolerance.

**Key Features:**
- **Batch merging**: Combines multiple approved PRs into a single "merge train" for testing, reducing CI minutes
- **Rollup strategy**: Tests all queued PRs together; if any fail, bisects to find the culprit
- **Dashboard UI**: A Phoenix LiveView dashboard showing queue status, history, and configuration
- **Priority system**: `P-high` and `P-low` labels control merge order
- **Timeout handling**: Automatic dequeue of stalled PRs after configurable timeout

**Docker Deployment:**

```yaml
# docker-compose.yml for Bors-ng
version: "3.8"
services:
  bors-ng:
    build:
      context: https://github.com/bors-ng/bors-ng.git#master
      args:
        SOURCE_COMMIT: latest
    ports:
      - "4000:4000"
    environment:
      - DATABASE_URL=ecto://postgres:password@db/bors_ng
      - SECRET_KEY_BASE=your-64-char-secret
      - GITHUB_CLIENT_ID=your_github_app_client_id
      - GITHUB_CLIENT_SECRET=your_github_app_secret
      - GITHUB_INTEGRATION_ID=your_integration_id
      - GITHUB_INTEGRATION_PEM_BASE64=your_base64_pem
      - HOST=your-domain.com
      - PORT=4000
    depends_on:
      - db
    restart: always

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=bors_ng
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: always

volumes:
  pgdata:
```

Bors-ng requires creating a GitHub App with specific permissions (repository contents: write, pull requests: read/write, commit statuses: write). The setup wizard at `/setup` walks through the OAuth flow and GitHub App configuration.

## Kodiak: Lightweight Auto-Merge with Smart Updates

Kodiak takes a different approach — instead of running a merge queue, it automatically updates and merges PRs that meet your criteria. It is significantly simpler to deploy than Bors-ng, requiring only a GitHub App installation with no database or persistent storage.

**Key Features:**
- **Auto-update**: Automatically rebases/merges PR branches when the base branch changes
- **Auto-merge**: Merges PRs as soon as they are approved and pass CI
- **Label-based configuration**: `.kodiak.toml` file for per-repository settings
- **Minimal footprint**: Single Python process, no database, no dashboard
- **Merge methods**: Supports merge, squash, and rebase strategies

**Docker Deployment:**

```yaml
# docker-compose.yml for Kodiak
version: "3.8"
services:
  kodiak:
    image: ghcr.io/chdsbd/kodiak:latest
    ports:
      - "8000:8000"
    environment:
      - GITHUB_APP_ID=your_app_id
      - GITHUB_APP_PRIVATE_KEY=/app/key.pem
      - GITHUB_APP_WEBHOOK_SECRET=your_webhook_secret
      - KODIAK_LOG_LEVEL=info
    volumes:
      - ./key.pem:/app/key.pem:ro
    restart: always
```

Kodiak is ideal for smaller teams that want merge automation without the operational overhead of a full merge queue. It is particularly effective when combined with GitHub branch protection rules requiring status checks before merging.

## Homu: The Original Merge Bot

Homu is the original merge bot that served the Rust compiler project for years before being replaced by Bors-ng. Despite its age, it remains a solid choice for teams that want a battle-tested, no-frills merge gating system.

**Key Features:**
- **Rollup testing**: Serializes PRs and tests them in batches
- **Bisection**: When a rollup fails, automatically identifies the problematic PR
- **Priority system**: `rollup-`, `rollup=always`, `rollup=maybe` labels
- **Lightweight**: Single Python process with SQLite storage
- **Rocket Science Rule**: Only merges code that passes CI on the latest revision

**Docker Deployment:**

```yaml
# docker-compose.yml for Homu
version: "3.8"
services:
  homu:
    build:
      context: https://github.com/rust-lang/homu.git#master
    ports:
      - "54856:54856"
    environment:
      - GITHUB_APP_ID=12345
      - GITHUB_APP_CLIENT_ID=your_client_id
      - GITHUB_APP_CLIENT_SECRET=your_client_secret
      - GITHUB_APP_PRIVATE_KEY=/app/private-key.pem
    volumes:
      - ./cfg.production.toml:/src/cfg.production.toml:ro
      - ./private-key.pem:/app/private-key.pem:ro
      - homu-data:/src/data
    restart: always

volumes:
  homu-data:
```

Homu's configuration is TOML-based and supports multiple repositories. It integrates with any CI system via webhooks — Homu watches for CI status updates and triggers merges automatically.

## Choosing the Right Merge Bot for Your Team

| Team Size | Recommendation | Why |
|-----------|---------------|-----|
| 1-5 developers | **Kodiak** | Simplest setup, auto-update handles most cases |
| 5-50 developers | **Bors-ng** | Full merge queue with dashboard, batch testing |
| 50+ developers | **Bors-ng** or **Homu** | Both handle high throughput; Bors-ng has better UI |
| Rust/OSS projects | **Homu** | Battle-tested by Rust, familiar to contributors |

Kodiak is the easiest to deploy — no database, no dashboard, just a GitHub App that auto-updates and merges PRs. Bors-ng requires more setup (PostgreSQL, GitHub App, OAuth) but provides a full-featured merge queue with a web dashboard. Homu is the simplest in architecture but the most manual to configure.

For teams already running [self-hosted CI/CD platforms](../woodpecker-ci-vs-drone-ci-vs-gitea-actions-self-hosted-cicd-guide-2026/), a merge queue bot is the logical next step to prevent broken main-branch builds.

## Deployment Architecture: Putting It All Together

A typical self-hosted merge queue deployment integrates three components:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│ GitHub/GitLab │────▶│ Merge Bot    │────▶│ CI System       │
│  Webhooks    │     │ (Bors/Kodiak)│     │ (Woodpecker/CI) │
└─────────────┘     └──────────────┘     └─────────────────┘
                            │                       │
                            │  Status Updates       │
                            ◀───────────────────────┘
```

1. Developer opens a PR and types `bors r+` (or applies an approval label)
2. Merge bot picks up the PR, rebases it onto the latest main
3. Merge bot creates a temporary merge commit and pushes it as a CI branch
4. CI system runs the full test suite on the temporary commit
5. If CI passes, the bot fast-forwards main to include the PR
6. If CI fails, the bot reports the failure and dequeues the PR

## Security Considerations for Merge Bots

Merge bots have write access to your main branch, making them a high-value target. Best practices include:

- **Minimal permissions**: Grant only the GitHub permissions the bot needs (contents: write, pull requests: read/write, statuses: write). Never grant admin or delete-branch permissions.
- **Webhook secret**: Use a strong, randomly generated webhook secret to prevent spoofed events
- **Internal network**: Run the merge bot within your private network, not exposed to the public internet
- **Audit logging**: Bors-ng and Homu both log all merge decisions — ship logs to your centralized logging system
- **Two-person rule**: Require at least one human approval before the bot can merge (configured via branch protection rules)

## FAQ

### Do merge queue bots work with GitLab?

Currently, all three bots are GitHub-only. Bors-ng has an open issue for GitLab support but no timeline. For GitLab, consider using GitLab's built-in Merge Trains feature (available in GitLab Premium/Ultimate) or the open-source `marge-bot`.

### How does a merge queue bot differ from GitHub's built-in merge queue?

GitHub's merge queue (beta) provides similar functionality but is a SaaS feature controlled by GitHub. Self-hosted bots give you full control over the queue logic, support custom gating rules, and keep all merge data on your infrastructure. Bors-ng and Homu also support batch testing (testing multiple PRs together) which GitHub's merge queue does not.

### Can I use a merge bot with monorepos?

Yes. All three bots handle monorepos well. Bors-ng and Homu's batch testing is particularly valuable for monorepos where cross-package breakage is common. Kodiak's per-repository configuration via `.kodiak.toml` lets you define path-specific merge rules (e.g., auto-merge docs changes but require CI for code changes).

### What happens when a batch merge fails?

Both Bors-ng and Homu implement bisection — when a batch of PRs fails CI, the bot tests smaller subsets until it identifies the specific PR(s) that caused the failure. The problematic PR is dequeued and the remaining PRs are re-tested and merged. This minimizes the impact of a single bad PR on the merge queue.

### How much maintenance do merge bots require?

Once configured, merge bots are remarkably low-maintenance. The primary ongoing task is keeping the GitHub App permissions and webhook secret up to date. Bors-ng requires PostgreSQL backups. Kodiak is the lowest maintenance — no database, auto-updating Docker image, and minimal configuration surface.

---

**💡 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Merge Queue & PR Gating Bots: Bors-ng vs Kodiak vs Homu Compared 2026",
  "description": "Compare self-hosted merge queue bots for automated PR gating. Deep dive into Bors-ng, Kodiak, and Homu with Docker Compose deployment guides, comparison tables, and practical recommendations for teams of all sizes.",
  "datePublished": "2026-06-17",
  "dateModified": "2026-06-17",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://pistack.xyz/logo.png"
    }
  }
}
</script>
