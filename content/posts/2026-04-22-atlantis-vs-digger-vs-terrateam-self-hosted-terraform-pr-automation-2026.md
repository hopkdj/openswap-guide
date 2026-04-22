---
title: "Atlantis vs Digger vs Terrateam: Self-Hosted Terraform PR Automation 2026"
date: 2026-04-22
tags: ["comparison", "guide", "self-hosted", "terraform", "iac", "devops", "gitops"]
draft: false
description: "Compare Atlantis, Digger, and Terrateam for self-hosted Terraform and OpenTofu pull request automation. Full Docker deployment guides, feature comparison, and integration walkthroughs."
---

If you manage infrastructure with Terraform or OpenTofu, running `terraform plan` and `terraform apply` manually is a bottleneck. Self-hosted Terraform pull request automation tools change that by running plans on every PR, posting results as comments, and applying changes through chat commands or merge triggers — all without a SaaS dependency.

In this guide, we compare three open-source options: **Atlantis**, **Digger**, and **Terrateam**. All three integrate with GitHub (and some with GitLab) to automate your IaC workflows from within your existing pull request flow.

| Tool | Stars | Language | License | Self-Hosted | GitHub | GitLab | Terraform | OpenTofu | Terragrunt |
|------|-------|----------|---------|-------------|--------|--------|-----------|----------|------------|
| [Atlantis](https://github.com/runatlantis/atlantis) | 9,012 | Go | Apache 2.0 | Yes | Yes | Yes | Yes | Yes | Limited |
| [Digger](https://github.com/diggerhq/digger) | 4,917 | Go | Apache 2.0 | Yes | Yes | Yes | Yes | Yes | Yes |
| [Terrateam](https://github.com/terrateamio/terrateam) | 1,221 | OCaml | Apache 2.0 | Yes | Yes | No | Yes | Yes | Yes |

## Why Self-Host Terraform PR Automation

Running Terraform in CI pipelines solves part of the problem, but dedicated PR automation tools offer several advantages:

- **State locking** — prevents concurrent modifications to the same infrastructure state
- **Plan previews** — see exactly what will change before merging
- **Apply via comments** — approve and apply infrastructure changes through PR comments
- **Policy enforcement** — gate applies behind approval workflows and cost estimates
- **Multi-environment support** — run different plans for dev, staging, and production
- **No vendor lock-in** — self-hosted tools keep your credentials, state, and policies under your control

If you are evaluating Terraform vs OpenTofu vs Pulumi for your IaC stack, these automation tools integrate with all three providers. For a deeper look at the IaC tools themselves, see our [OpenTofu vs Terraform vs Pulumi comparison](../opentofu-vs-terraform-vs-pulumi-self-hosted-iac-guide-2026/).

## Atlantis: The Established Standard

Atlantis is the most widely adopted self-hosted Terraform PR automation tool. It runs as a persistent server that receives webhook events from GitHub or GitLab, executes `terraform plan` and `terraform apply` in isolated workspaces, and posts the results back to your pull requests.

### Architecture

Atlantis follows a server-based model:

```
GitHub PR → Webhook → Atlantis Server → terraform plan/apply → PR Comment
                                                    ↓
                                             State File (S3/GCS/local)
```

Key characteristics:

- **Single binary** — easy to deploy as a Docker container
- **Workspace isolation** — each repo/dir/workspace gets its own state directory
- **Lock management** — automatic state locking prevents concurrent applies
- **Multi-tenancy** — server-level or repo-level configuration
- **Server-side config** — `repos.yaml` defines allowed repos, workflows, and policies

### Docker Compose Deployment

Atlantis provides an official Docker Compose setup for local development. For production, you will want to add persistent volumes and external state storage:

```yaml
version: "3.8"

services:
  atlantis:
    image: ghcr.io/runatlantis/atlantis:latest
    ports:
      - "4141:4141"
    environment:
      - ATLANTIS_GH_USER=your-github-user
      - ATLANTIS_GH_TOKEN=your-github-token
      - ATLANTIS_GH_WEBHOOK_SECRET=your-webhook-secret
      - ATLANTIS_REPO_ALLOWLIST=github.com/your-org/*
      - ATLANTIS_ATLANTIS_URL=https://atlantis.example.com
      - ATLANTIS_DEFAULT_TF_VERSION=1.9.0
      # Optional: S3 backend for remote state
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_DEFAULT_REGION=us-east-1
    volumes:
      - atlantis-data:/home/atlantis/.atlantis
      - ./repos.yaml:/etc/atlantis/repos.yaml
    command: ["server", "--config", "/etc/atlantis/repos.yaml"]
    restart: unless-stopped

volumes:
  atlantis-data:
```

### Atlantis Server Configuration

The `repos.yaml` file controls which repositories Atlantis can manage and what workflows it runs:

```yaml
repos:
  - id: /.*/
    apply_requirements: [approved]
    allowed_overrides: [workflow, apply_requirements]
    workflow: default
    allowed_commands: [plan, apply, unlock]

workflows:
  default:
    plan:
      steps:
        - init
        - plan
    apply:
      steps:
        - apply

# Enable policy checks with Conftest
policy_checks:
  - name: cost-estimate
    path: policies/cost.rego
```

With this configuration, Atlantis requires PR approval before any apply, and runs Conftest policy checks on every plan. You can combine this with IaC security scanning — see our [Checkov vs tfsec vs Trivy guide](../checkov-vs-tfsec-vs-trivy-self-hosted-iac-security-scanning-2026/) for policy-as-code options.

### Pros and Cons

**Pros:**

- Largest community and most battle-tested
- Excellent GitHub and GitLab support
- Rich webhook-triggered workflow system
- Strong multi-environment support with project-based configuration
- Mature approval and locking mechanisms

**Cons:**

- Server must be publicly reachable for webhooks (ngrok or reverse proxy required)
- No native Terragrunt support
- Configuration can become complex at scale
- No built-in drift detection (requires external scheduling)

## Digger: CI-Native IaC Orchestration

Digger takes a different approach. Instead of running a persistent server, Digger executes IaC commands directly inside your existing CI pipeline (GitHub Actions, GitLab CI, Bitbucket Pipelines). This means no additional infrastructure to manage — your CI runners handle the execution.

### Architecture

Digger's CI-native model works like this:

```
GitHub PR → GitHub Actions Workflow → Digger CLI → terraform plan/apply → PR Comment
```

Key characteristics:

- **No server to maintain** — runs in your CI pipeline
- **Terragrunt native** — first-class support for Terragrunt workflows
- **Profile-based self-hosting** — optional platform mode for centralized management
- **Drift detection** — built-in scheduled drift checking
- **OpenTofu support** — works with both Terraform and OpenTofu

### Docker Compose Deployment (Platform Mode)

While Digger's primary mode runs in CI, it also offers a self-hosted platform mode for centralized orchestration and drift detection. The full setup includes multiple PostgreSQL databases and several services:

```yaml
version: "3.8"

services:
  postgres-orchestrator:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_PASSWORD=changeme
      - POSTGRES_DB=orchestrator
    volumes:
      - postgres-orchestrator-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  postgres-statesman:
    image: postgres:16-alpine
    ports:
      - "5433:5432"
    environment:
      - POSTGRES_PASSWORD=changeme
      - POSTGRES_DB=statesman
    volumes:
      - postgres-statesman-data:/var/lib/postgresql/data

  orchestrator:
    image: diggerhq/orchestrator:latest
    profiles: ["platform", "all"]
    env_file:
      - orchestrator.env
    environment:
      - BACKGROUND_JOBS_CLIENT_TYPE=internal
      - DATABASE_URL=postgres://postgres:changeme@postgres-orchestrator:5432/orchestrator
    depends_on:
      postgres-orchestrator:
        condition: service_healthy
    ports:
      - "3100:3100"

  ui:
    image: diggerhq/ui:latest
    profiles: ["platform", "all"]
    env_file:
      - ui.env
    ports:
      - "3000:3000"
    depends_on:
      - orchestrator

  drift-scheduler:
    image: diggerhq/drift:latest
    profiles: ["platform", "all"]
    env_file:
      - drift.env
    environment:
      - DATABASE_URL=postgres://postgres:changeme@postgres-statesman:5432/statesman
    depends_on:
      postgres-statesman:
        condition: service_healthy

volumes:
  postgres-orchestrator-data:
  postgres-statesman-data:
```

### Digger CI Configuration

For the CI-native mode (the most common deployment), add a GitHub Actions workflow to your IaC repository:

```yaml
name: Digger IaC
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

permissions:
  contents: read
  pull-requests: write
  statuses: write

jobs:
  digger:
    runs-on: ubuntu-latest
    name: Run IaC
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Digger Run
        uses: diggerhq/digger@v0.0.37
        with:
          setup-aws: true
          setup-backend: "s3"
          bucket-name: "your-terraform-state-bucket"
          dynamodb-table: "terraform-lock-table"
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_DEFAULT_REGION: "us-east-1"
          GITHUB_CONTEXT: ${{ toJson(github) }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Digger reads a `digger.yml` configuration file from your repository root:

```yaml
projects:
  - name: production
    dir: infra/production
    workflow:
      plan:
        steps:
          - init:
              extra_args: ["-backend-config=backend.tfvars"]
          - plan:
              extra_args: ["-var-file=production.tfvars"]
      apply:
        steps:
          - apply:
              extra_args: ["-auto-approve"]
  - name: staging
    dir: infra/staging
    workflow:
      plan:
        steps:
          - init
          - plan
      apply:
        steps:
          - apply

policies:
  - name: cost-limit
    type: cost
    threshold: 100
```

### Pros and Cons

**Pros:**

- Zero server infrastructure required for CI mode
- Native Terragrunt and OpenTofu support
- Built-in drift detection scheduler
- Simpler operational model — no webhook endpoints to expose
- Leverages your existing CI runner capacity

**Cons:**

- CI-native mode requires GitHub Actions / GitLab CI (not standalone)
- Platform mode adds complexity with multiple databases
- Smaller community than Atlantis
- Fewer third-party integrations and plugins

## Terrateam: GitOps-First Infrastructure Orchestration

Terrateam is a newer entrant that positions itself as a GitOps tool for infrastructure. Written in OCaml, it integrates with GitHub to automate Terraform, OpenTofu, CDKTF, Terragrunt, and Pulumi workflows through pull requests.

### Architecture

Terrateam follows a webhook-server model similar to Atlantis but with a GitOps-first philosophy:

```
GitHub PR → Webhook → Terrateam Server → IaC plan/apply → PR Comment + Status Check
```

Key characteristics:

- **GitOps-first** — configuration lives in `.terrateam/config.yml` in your repo
- **Multi-IaC support** — Terraform, OpenTofu, CDKTF, Terragrunt, Pulumi
- **Workflow tags** — tag-based workflow execution for granular control
- **Built-in status checks** — GitHub status checks gate merges on plan success

### Docker Deployment

Terrateam can be self-hosted via Docker. Here is a production-ready setup:

```yaml
version: "3.8"

services:
  terrateam:
    image: terrateam/terrateam:latest
    ports:
      - "3000:3000"
    environment:
      - TERRATEAM_GITHUB_APP_ID=your-app-id
      - TERRATEAM_GITHUB_APP_INSTALLATION_ID=your-installation-id
      - TERRATEAM_GITHUB_PRIVATE_KEY_PATH=/etc/terrateam/private-key.pem
      - TERRATEAM_GITHUB_WEBHOOK_SECRET=your-webhook-secret
      - TERRATEAM_LOG_LEVEL=info
    volumes:
      - ./github-app-private-key.pem:/etc/terrateam/private-key.pem:ro
      - terrateam-data:/var/lib/terrateam
    restart: unless-stopped

volumes:
  terrateam-data:
```

### Terrateam Configuration

Configuration lives in `.terrateam/config.yml` at the root of your infrastructure repository:

```yaml
workflows:
  - tag_query: "env:production"
    init:
      extra_args: ["-backend-config=backend-prod.tfvars"]
    plan:
      extra_args: ["-var-file=production.tfvars"]
    apply:
      extra_args: ["-auto-approve"]
      require_approval: true

  - tag_query: "env:staging"
    plan:
      extra_args: ["-var-file=staging.tfvars"]
    apply:
      require_approval: false

policies:
  - name: require-approval-prod
    type: approval
    environments: ["production"]
    min_approvals: 2

hooks:
  - event: plan
    command: |
      echo "Plan output:"
      cat $TERRATEAM_PLAN_OUTPUT
```

Terrateam's tag-based system lets you run different workflows for different environments by applying labels to your PRs. A PR tagged with `env:production` runs the production workflow, while `env:staging` runs the staging workflow.

### Pros and Cons

**Pros:**

- Strong GitOps-first design — configuration versioned in the repo
- Broadest IaC tool support (Terraform, OpenTofu, CDKTF, Terragrunt, Pulumi)
- Tag-based workflow execution for fine-grained control
- GitHub App authentication for cleaner permissions model
- Smaller, focused codebase

**Cons:**

- Youngest project with the smallest community
- GitHub only — no GitLab support
- OCaml codebase makes contributions harder for most developers
- Limited third-party integrations compared to Atlantis
- Fewer deployment examples and community resources

## Feature Comparison

| Feature | Atlantis | Digger (CI) | Digger (Platform) | Terrateam |
|---------|----------|-------------|-------------------|-----------|
| GitHub support | Yes | Yes | Yes | Yes |
| GitLab support | Yes | Yes | Yes | No |
| Self-hosted | Yes | N/A (CI-native) | Yes | Yes |
| Terraform | Yes | Yes | Yes | Yes |
| OpenTofu | Yes | Yes | Yes | Yes |
| Terragrunt | Limited | Yes | Yes | Yes |
| Pulumi | No | No | No | Yes |
| CDKTF | No | No | No | Yes |
| Drift detection | No (external) | Yes | Yes | No |
| State locking | Yes | Yes (native) | Yes | Yes |
| Approval workflows | Yes | Yes | Yes | Yes |
| Policy as code | Conftest | Built-in cost | Built-in cost | Custom |
| Multi-environment | Yes | Yes | Yes | Yes (tags) |
| Cost estimation | Infracost | Built-in | Built-in | No |
| Web UI | Basic | Yes (platform) | Yes | No |
| GitHub App auth | No | No | No | Yes |
| Server infrastructure | Required | None | Required | Required |

## Which Tool Should You Choose?

**Choose Atlantis if:**

- You need the most mature and widely-adopted solution
- You use GitLab and need multi-VCS support
- You want extensive community resources and plugins
- Your team is already familiar with server-based webhook automation

**Choose Digger if:**

- You want zero server infrastructure (CI-native mode)
- You use Terragrunt extensively and need native support
- You want built-in drift detection and cost estimation
- You prefer running everything inside GitHub Actions or GitLab CI

**Choose Terrateam if:**

- You want a GitOps-first approach with config in your repo
- You use Pulumi or CDKTF alongside Terraform
- You prefer GitHub App authentication over personal access tokens
- You value tag-based workflow selection for multi-environment setups

For teams already using GitOps workflows, combining these tools with a GitOps platform like ArgoCD or Flux creates a complete automation pipeline — from infrastructure changes through deployment. See our [ArgoCD vs Flux guide](../argocd-vs-flux-self-hosted-gitops-guide/) for platform comparison.

## FAQ

### What is Terraform pull request automation?

Terraform PR automation tools run `terraform plan` automatically when you open a pull request and post the plan output as a PR comment. They can also execute `terraform apply` through approved PR comments or merge events, eliminating the need for developers to run Terraform commands locally or manage CI pipelines manually.

### Is Atlantis still maintained in 2026?

Yes. Atlantis remains actively maintained with regular releases. As of April 2026, it has over 9,000 GitHub stars and receives frequent commits. The project transitioned to community maintenance and continues to support both Terraform and OpenTofu.

### Can these tools work with OpenTofu instead of Terraform?

All three tools support OpenTofu. Atlantis supports OpenTofu through its `--tofu-bin-path` flag or by setting `ATLANTIS_DEFAULT_TOFU_VERSION`. Digger natively supports OpenTofu as a drop-in replacement. Terrateam works with any Terraform-compatible CLI, including OpenTofu.

### Do I need to expose my server to the internet for webhooks?

Atlantis and Terrateam both require webhook endpoints that GitHub or GitLab can reach. Options include:
- A reverse proxy with a public domain and TLS certificate
- Ngrok or similar tunneling for development
- Placing the server inside a VPC with a load balancer that has a public endpoint

Digger in CI-native mode avoids this entirely since it runs inside your CI pipeline and does not need an inbound webhook endpoint.

### How do these tools handle Terraform state locking?

Atlantis manages state locking at the server level — it tracks which workspace is currently being planned or applied and blocks concurrent operations. Digger relies on your Terraform backend's native locking (S3 + DynamoDB, GCS, etc.). Terrateam also uses native backend locking. For production setups, always configure a remote backend with locking to prevent state corruption.

### Can I run infrastructure drift detection with these tools?

Digger (both CI and Platform modes) includes built-in drift detection that runs on a schedule and creates PRs when drift is detected. Atlantis does not have native drift detection — you need to schedule `terraform plan` externally using cron jobs or CI pipelines. Terrateam does not include built-in drift detection either. For dedicated drift detection tooling, see our [infrastructure drift detection guide](../self-hosted-infrastructure-drift-detection-driftctl-cloud-custodian-opentofu-guide-2026/).

### How do I set up approval workflows?

Atlantis uses `apply_requirements` in `repos.yaml` to enforce approval gates (e.g., `approved`, `mergeable`). Digger supports approval through GitHub's required review system and its own `require_approval` config. Terrateam uses policy-based approval rules defined in `.terrateam/config.yml` with configurable minimum approval counts per environment.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Atlantis vs Digger vs Terrateam: Self-Hosted Terraform PR Automation 2026",
  "description": "Compare Atlantis, Digger, and Terrateam for self-hosted Terraform and OpenTofu pull request automation. Full Docker deployment guides, feature comparison, and integration walkthroughs.",
  "datePublished": "2026-04-22",
  "dateModified": "2026-04-22",
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
