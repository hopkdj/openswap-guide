---
title: "Self-Hosted Git Mirror & Replication — Gitea Mirror, GitLab Replication, Gitolite Guide"
date: 2026-05-05
tags: ["git", "replication", "mirror", "self-hosted", "devops", "backup"]
draft: false
---

Git repositories are the foundation of modern software development. When your codebase grows beyond a single server — whether for disaster recovery, geo-distributed teams, or CI/CD redundancy — you need reliable mirror and replication solutions. While hosted platforms offer built-in replication, self-hosted alternatives give you full control over your source code infrastructure.

This guide compares three approaches to self-hosted Git mirroring and replication: **Gitea Mirror** (built-in pull/push mirroring), **GitLab Geo** (multi-node replication), and **Gitolite** (access-controlled Git hosting with manual mirroring). We will cover deployment, configuration, and trade-offs for each.

## Understanding Git Mirroring vs Replication

Before diving into tools, it is important to distinguish between two approaches:

- **Mirroring**: One-way or two-way copy of a repository to another location. Typically pull-based (the mirror fetches from the primary). Simpler, but with potential lag.
- **Replication**: Real-time or near-real-time synchronization, often with multi-master support. More complex but provides higher availability.

Most self-hosted solutions use mirroring because Git's distributed nature makes full replication unnecessary for many use cases.

## Gitea Mirror — Built-In Git Repository Mirroring

Gitea (and its community fork Forgejo) includes a native mirroring system that supports both pull and push mirrors. This is the simplest approach for most self-hosted Git setups.

### Gitea Pull Mirror Configuration

A pull mirror periodically fetches from a source repository and updates the local copy:

```yaml
# docker-compose.yml for Gitea with mirror enabled
version: "3.8"
services:
  gitea:
    image: gitea/gitea:latest
    container_name: gitea
    environment:
      - USER_UID=1000
      - USER_GID=1000
      - GITEA__repository__ENABLE_PUSH_MIRROR=true
      - GITEA__repository__ENABLE_PULL_MIRROR=true
    ports:
      - "3000:3000"
      - "222:22"
    volumes:
      - gitea-data:/data
      - /etc/timezone:/etc/timezone:ro
      - /etc/localtime:/etc/localtime:ro
    restart: unless-stopped

  gitea-db:
    image: postgres:15
    environment:
      - POSTGRES_USER=gitea
      - POSTGRES_PASSWORD=gitea_secret
      - POSTGRES_DB=gitea
    volumes:
      - gitea-db:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  gitea-data:
  gitea-db:
```

After deployment, configure mirrors through the Gitea web UI:
1. Navigate to **Settings -> Repository -> Mirror Settings**
2. Enable **Pull Mirror** and set the remote URL
3. Set the mirror interval (default: every 8 hours, configurable via `MIRROR_INTERVAL`)
4. For push mirrors, add the destination URL and optional authentication token

### Gitea Mirror CLI Automation

For headless or automated setups, you can use the Gitea API:

```bash
# Create a pull mirror via API
curl -X POST "https://gitea.example.com/api/v1/repos/{owner}/{repo}/mirror-sync" \
  -H "Authorization: token $GITEA_TOKEN" \
  -H "Content-Type: application/json"

# Force sync all mirrors
curl -X POST "https://gitea.example.com/api/v1/admin/mirror/repo-sync" \
  -H "Authorization: token $ADMIN_TOKEN"
```

## GitLab Geo — Multi-Node Repository Replication

GitLab Geo provides a more comprehensive replication system designed for enterprise-scale setups with multiple data centers. It replicates repositories, LFS objects, CI artifacts, and database changes across primary and secondary nodes.

### GitLab Geo Architecture

GitLab Geo uses a primary-secondary architecture:
- **Primary node**: The main GitLab instance where all writes occur
- **Secondary nodes**: Read-only replicas that receive data from the primary via asynchronous replication

### GitLab Geo Docker Compose Setup

```yaml
# docker-compose.yml for GitLab Geo secondary node
version: "3.8"
services:
  gitlab-secondary:
    image: gitlab/gitlab-ee:latest
    container_name: gitlab-geo-secondary
    hostname: gitlab-secondary.example.com
    environment:
      - GITLAB_OMNIBUS_CONFIG=|
        external_url 'https://gitlab-secondary.example.com'
        gitlab_rails['geo_role'] = 'secondary'
        gitlab_rails['geo_node_name'] = 'secondary-1'
        gitlab_rails['geo_primary_node_url'] = 'https://gitlab-primary.example.com'
        postgresql['sql_user_password'] = 'gitlab_geodb_password'
    ports:
      - "443:443"
      - "80:80"
      - "22:22"
    volumes:
      - gitlab-config:/etc/gitlab
      - gitlab-logs:/var/log/gitlab
      - gitlab-data:/var/opt/gitlab
    restart: unless-stopped

volumes:
  gitlab-config:
  gitlab-logs:
  gitlab-data:
```

### GitLab Geo Verification

After configuration, verify replication status:

```bash
# Check Geo node status on primary
docker exec gitlab gitlab-rake gitlab:geo:status

# Check replication status on secondary
docker exec gitlab-geo gitlab-rake gitlab:geo:check

# View replication events in admin dashboard
# Navigate to Admin -> Geo -> Nodes
```

GitLab Geo supports selective replication (choose which projects to replicate) and conflict detection for multi-master scenarios.

## Gitolite — Access-Controlled Git Hosting with Manual Mirroring

Gitolite is a lightweight Git server that provides fine-grained access control through SSH. While it does not have built-in automated mirroring like Gitea, its simplicity makes it ideal for manual mirror setups using Git's native push/pull mechanisms.

### Gitolite Installation

```bash
# Install on the server
sudo apt-get update && sudo apt-get install -y gitolite3

# Set up the admin key
sudo -u git gl-setup /home/admin/.ssh/id_rsa.pub

# Clone the gitolite-admin repo to manage repos and access
git clone git@yourserver:gitolite-admin
```

### Gitolite Mirror Setup

Create a mirror configuration using Git's native mirroring:

```bash
# On the primary server, configure a push mirror
cd /home/git/repositories/myproject.git
git remote add mirror git@mirror-server:myproject.git
git config --add remote.mirror.mirror true
git config --add remote.mirror.push "+refs/*:refs/*"

# Set up a cron job to sync
echo "*/15 * * * * cd /home/git/repositories/myproject.git && git push --mirror mirror" | crontab -
```

### Gitolite Access Control for Mirrors

```
# In gitolite-admin/conf/gitolite.conf
repo myproject
    RW+     =   @developers
    R       =   @readonly
    -       =   mirror-user
```

## Comparison: Git Mirror and Replication Solutions

| Feature | Gitea Mirror | GitLab Geo | Gitolite + Manual |
|---------|-------------|------------|-------------------|
| **Setup complexity** | Low | High | Medium |
| **Automated mirroring** | Yes (pull/push) | Yes (Geo replication) | No (manual/cron) |
| **Multi-master** | No | Partial (via Geo) | No |
| **Web UI** | Yes | Yes | No |
| **LFS support** | Yes | Yes | Limited |
| **Access control** | Built-in | Built-in | SSH-based (fine-grained) |
| **Resource usage** | Low (~200MB RAM) | High (~4GB+ RAM) | Very low (~50MB RAM) |
| **CI/CD integration** | Gitea Actions | GitLab CI | External |
| **Best for** | Small-medium teams | Enterprise multi-DC | Minimalist setups |

## When to Choose Each Solution

**Choose Gitea Mirror** when you need simple, automated repository mirroring with a web interface. It is lightweight, easy to deploy, and works well for teams of 5-50 developers.

**Choose GitLab Geo** when you operate across multiple data centers and need full-stack replication (repos, CI artifacts, LFS objects, database). It requires significant resources but provides the most comprehensive solution.

**Choose Gitolite** when you want maximum control with minimal resource usage. Ideal for infrastructure teams that manage dozens of repositories and prefer SSH-based workflows.

## Mirror Monitoring and Health Checks

Regardless of which solution you choose, monitoring mirror health is critical:

```bash
# Check Gitea mirror sync status
curl -s "https://gitea.example.com/api/v1/repos/{owner}/{repo}" \
  -H "Authorization: token $TOKEN" | jq '.mirror_updated_at'

# Check GitLab Geo replication lag
curl -s "https://gitlab.example.com/api/v4/geo_nodes/status" \
  -H "PRIVATE-TOKEN: $TOKEN" | jq '.[].last_event_id'

# Verify Git mirror integrity
git fsck --full
git reflog expire --expire=now --all
git gc --prune=now
```

For related reading, see our [Gitea vs Forgejo vs GitLab CE comparison](../gitea-vs-forgejo-vs-gitlab-ce-self-hosted-git-forge/) and [CI/CD pipeline guide with Gitea Actions](../woodpecker-ci-vs-drone-ci-vs-gitea-actions-self-hosted-cicd-guide-2026/). If you manage package repositories, our [binary repository guide](../artifactory-oss-vs-nexus-vs-pulp-self-hosted-binary-repository-guide/) covers the next layer of the supply chain.

## Why Self-Host Git Mirrors?

Hosting your own Git mirrors provides several advantages over relying on third-party platforms. First, **data sovereignty** ensures your code never leaves infrastructure you control — critical for regulated industries and organizations with strict compliance requirements.

Second, **disaster recovery** becomes straightforward when you maintain geographically distributed mirrors. If your primary server goes offline, developers can pull from a mirror and continue working. For CI/CD pipelines, mirrors reduce network latency and provide redundancy during outages.

Third, **cost predictability** eliminates per-user or per-storage fees that hosted platforms charge. With self-hosted solutions, your only costs are the servers you provision.

For teams managing multiple projects, combining Git mirrors with [backup verification strategies](../2026-04-19-self-hosted-backup-verification-testing-integrity-guide/) ensures your repositories survive hardware failures.

## FAQ

### What is the difference between Git mirror and Git clone?
A Git clone creates a one-time copy of a repository. A Git mirror is an ongoing synchronization — either pull-based (mirror fetches updates from source) or push-based (source pushes updates to mirror). Mirrors are kept up-to-date automatically, while clones are static snapshots.

### How often should Git mirrors sync?
For most teams, syncing every 15-30 minutes is sufficient. High-velocity teams may want 1-5 minute intervals. Gitea's default is 8 hours, but this is configurable via the `MIRROR_INTERVAL` setting. GitLab Geo replicates in near real-time (typically within 30 seconds).

### Can Gitea mirror private repositories?
Yes. Gitea supports mirroring both public and private repositories. For private remote repositories, provide an access token or SSH key in the mirror URL configuration.

### Does GitLab Geo work with GitLab CE (Community Edition)?
No. GitLab Geo is only available in GitLab Enterprise Edition. For CE users, consider Gitea/Forgejo mirroring or manual Git replication scripts as alternatives.

### How do I verify Git mirror integrity?
Run `git fsck --full` on the mirrored repository to check for corruption. You can also compare commit counts (`git rev-list --count HEAD`) between primary and mirror, or use Gitea's built-in mirror sync status API to verify the last successful sync time.

### What happens if a Git mirror falls behind?
If a mirror falls significantly behind (e.g., due to network issues), most solutions will automatically catch up on next sync. GitLab Geo tracks replication events and can replay missed changes. For manual mirrors, you may need to force-push or re-clone from the primary.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Git Mirror and Replication — Gitea Mirror, GitLab Replication, Gitolite Guide",
  "description": "Compare self-hosted Git mirroring and replication solutions: Gitea Mirror, GitLab Geo, and Gitolite. Includes Docker Compose configs, setup guides, and monitoring.",
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
