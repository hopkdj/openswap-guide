---
title: "Gerrit vs Review Board vs Phorge: Best Self-Hosted Code Review Platforms 2026"
date: 2026-04-14
tags: ["comparison", "guide", "self-hosted", "code-review", "collaboration"]
draft: false
description: "A comprehensive comparison of the best self-hosted code review platforms in 2026. Learn how to deploy Gerrit, Review Board, and Phorge with Docker, and choose the right tool for your team's review workflow."
---

Code review is the single most impactful practice a development team can adopt to catch bugs early, share knowledge, and maintain consistent quality across a codebase. While platforms like GitHub and GitLab bundle code review into their broader offerings, many organizations need standalone review systems — whether because they already use a Git forge without built-in review, require granular permission controls, or want to keep review data fully isolated on their own infrastructure.

In 2026, the landscape of self-hosted code review tools is richer than ever. This guide compares three mature, production-ready platforms — **Gerrit**, **Review Board**, and **Phorge** (the community-maintained fork of Phabricator) — with hands-on deployment instructions so you can get any of them running on your own servers today.

## Why Self-Host Your Code Review Platform

Running your own code review system delivers advantages that go well beyond privacy:

**Deep integration with existing infrastructure.** Self-hosted review tools connect directly to your LDAP/Active Directory, internal Git servers, CI pipelines, and ticketing systems without relying on OAuth providers or third-party APIs.

**Granular access control.** Enterprise review workflows often require fine-grained permissions — branch-level read access, mandatory reviewer assignments, per-project score thresholds, and audit logging. Self-hosted platforms let you configure these policies exactly as your organization demands.

**No per-seat licensing costs.** Cloud code review tools frequently charge per user per month. With self-hosted software, you pay for the server, not the headcount. Onboarding ten new developers costs nothing.

**Custom workflows and extensions.** Open-source review platforms expose APIs, webhooks, and plugin architectures. You can build custom pre-submit checks, integrate with internal compliance databases, or automate review assignment based on file ownership maps.

**Regulatory compliance.** For teams in finance, healthcare, or government, keeping review metadata — who reviewed what, when, and what comments were made — inside your own network is often a regulatory requirement, not an option.

---

## Gerrit: The Patch-Centric Powerhouse

Gerrit is arguably the most widely deployed self-hosted code review system in the world. Originally developed for the Android Open Source Project, it powers code review for thousands of organizations — from Google and the Linux kernel project to countless mid-size engineering teams.

### Core Philosophy

Gerrit's defining concept is the **patch set** model. Instead of reviewing pull requests that merge entire branches, contributors push individual commits to a special `refs/for/<branch>` namespace. Each commit becomes a reviewable unit that accumulates feedback, CI results, and scores before being submitted (merged) by a user with submit permission.

This model is particularly powerful for large projects with many concurrent contributors, because it enforces a linear, commit-by-commit review process that keeps history clean and makes it easy to track exactly which changes landed when.

### Key Features

- Patch-set-based review with threaded inline comments
- Mandatory code-owner approvals via configurable score labels (`Code-Review`, `Verified`, etc.)
- Built-in OAuth, LDAP, HTTP, and SSH authentication
- Plugin architecture with hundreds of community plugins
- REST API and stream-events for real-time webhooks
- Native Git over SSH and HTTP protocols
- Integration with CI systems via the `Verified` label
- Submit strategies: merge, rebase, cherry-pick, or fast-forward only

### Installation with Docker Compose

Gerrit ships as a single Java application. The official Docker image makes deployment straightforward:

```yaml
# docker-compose.yml
version: "3.8"

services:
  gerrit:
    image: gerritcodereview/gerrit:3.10.4
    container_name: gerrit
    restart: unless-stopped
    ports:
      - "8080:8080"   # Web UI
      - "29418:29418" # SSH
    environment:
      - CANONICAL_WEB_URL=http://review.example.com:8080
    volumes:
      - gerrit_data:/var/gerrit/review_site
    networks:
      - review-net

  gerrit-init:
    image: gerritcodereview/gerrit:3.10.4
    container_name: gerrit-init
    entrypoint: /bin/sh
    command: -c "
      java -jar /var/gerrit/bin/gerrit.war init --batch \
        --install-all-plugins \
        -d /var/gerrit/review_site && \
      echo 'auth.type = HTTP' >> /var/gerrit/review_site/etc/gerrit.config && \
      echo 'gitweb.type = gitiles' >> /var/gerrit/review_site/etc/gerrit.config
    "
    volumes:
      - gerrit_data:/var/gerrit/review_site

volumes:
  gerrit_data:

networks:
  review-net:
    driver: bridge
```

After bringing the stack up, create the initial admin account:

```bash
# Start Gerrit
docker compose up -d

# Wait for initialization (check logs)
docker compose logs -f gerrit

# Register the first user via the web UI at http://localhost:8080
# This user becomes the administrator
```

For production deployments, you will want to configure a reverse proxy, set up LDAP authentication, and provision a PostgreSQL database backend instead of the embedded H2 database:

```ini
# gerrit.config (excerpt for production)
[database]
    type = postgresql
    hostname = db.review.internal
    port = 5432
    database = reviewdb
    username = gerrit

[auth]
    type = LDAP

[ldap]
    server = ldap://ldap.internal
    username = cn=gerrit,ou=services,dc=example,dc=com
    accountBase = ou=people,dc=example,dc=com
    accountPattern = (uid=${username})
    accountFullName = displayName
    accountEmailAddress = mail
```

### Review Workflow

1. A developer creates a branch, makes commits, and pushes to `refs/for/main`:
   ```bash
   git push origin HEAD:refs/for/main
   ```

2. Gerrit creates a change request. Reviewers see the diff, leave inline comments, and assign scores (typically `-2` to `+2` for `Code-Review`).

3. CI systems run tests and report a `Verified` score (`-1` for failure, `+1` for success).

4. When all required scores are met, an authorized user clicks **Submit** to merge.

### Pros and Cons

| Pros | Cons |
|------|------|
| Battle-tested at massive scale (Android, Linux) | Steep learning curve for contributors |
| Excellent for high-volume, multi-contributor projects | UI feels dated compared to modern Git forges |
| Rich plugin ecosystem | Plugin quality varies; some are unmaintained |
| Strong access control and submit strategies | Java-based — requires significant memory (2 GB+ minimum) |
| SSH-native workflow is fast for CLI users | Initial configuration is complex |

---

## Review Board: The Universal Review Platform

Review Board takes a different approach. Instead of being Git-specific, it is designed to work with virtually any version control system — Git, Mercurial, Subversion, Perforce, CVS, Bazaar, and more. This makes it an ideal choice for organizations with heterogeneous repositories or legacy systems.

### Core Philosophy

Review Board centers on **review requests** — each one represents a set of changes that need approval. Reviewers can comment on specific lines, request changes, and mark the request as "Ship It" when satisfied. The platform is designed to be lightweight, fast, and easy to adopt regardless of the underlying VCS.

### Key Features

- Multi-VCS support: Git, Mercurial, Subversion, Perforce, CVS, Bazaar
- Diff viewer with syntax highlighting and side-by-side comparison
- File-by-file review with inline comments
- Review groups and per-repository permissions
- Email notifications and configurable review workflows
- REST API with Python bindings
- RBTools command-line client for posting reviews from the terminal
- Extensions framework with community-contributed extensions
- Built-in screenshot annotation for UI/UX reviews
- Dark mode support in the web interface

### Installation with Docker Compose

Review Board provides an official Docker image that bundles the application, database, and search engine:

```yaml
# docker-compose.yml
version: "3.8"

services:
  reviewboard:
    image: reviewboard/reviewboard:6.2
    container_name: reviewboard
    restart: unless-stopped
    ports:
      - "8080:80"
    environment:
      - SITE_ROOT=/
      - ADMIN_USER=admin
      - ADMIN_PASSWORD=SecurePass2026!
      - ADMIN_EMAIL=admin@example.com
      - DATABASE_TYPE=postgresql
      - DATABASE_HOST=db
      - DATABASE_PORT=5432
      - DATABASE_NAME=reviewboard
      - DATABASE_USER=rbuser
      - DATABASE_PASSWORD=RBPass2026!
    volumes:
      - rb_media:/var/www/reviewboard/data/media
      - rb_static:/var/www/reviewboard/data/static
      - rb_conf:/etc/reviewboard
    depends_on:
      - db
      - memcached
    networks:
      - review-net

  db:
    image: postgres:16-alpine
    container_name: rb-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=reviewboard
      - POSTGRES_USER=rbuser
      - POSTGRES_PASSWORD=RBPass2026!
    volumes:
      - pg_data:/var/lib/postgresql/data
    networks:
      - review-net

  memcached:
    image: memcached:1.6-alpine
    container_name: rb-memcached
    restart: unless-stopped
    networks:
      - review-net

volumes:
  rb_media:
  rb_static:
  rb_conf:
  pg_data:

networks:
  review-net:
    driver: bridge
```

After the stack starts, configure your first repository:

```bash
# Access the web UI
open http://localhost:8080

# Add a repository through Admin > Repositories
# For a Git repository served via HTTPS:
#   Repository Type: Git
#   Path: https://git.example.com/org/project.git
#   Mirroring Path: (leave empty for single-server setups)
```

Install RBTools for command-line review posting:

```bash
pip install RBTools

# Create a .reviewboardrc in your repository root:
cat > .reviewboardrc << 'EOF'
REVIEWBOARD_URL = "http://reviewboard.example.com"
REPOSITORY = "my-project"
EOF

# Post a review request from a branch:
rbt post --diff-only main..feature-branch
```

### Review Workflow

1. A developer posts a diff using `rbt post` or the web UI's "New Review Request" button.

2. The diff is parsed and displayed in the web viewer. Reviewers can navigate file-by-file, click on specific lines to add comments, and use the "Ship It" button to approve.

3. The developer addresses feedback, uploads an updated diff, and the cycle repeats.

4. Once approved, the changes are merged using your standard VCS workflow (the platform does not merge for you).

### Pros and Cons

| Pros | Cons |
|------|------|
| Supports virtually any version control system | Not Git-specific — lacks some Git-native features |
| Clean, intuitive web interface | No built-in merge capability |
| Lightweight and fast (Python + Django) | Smaller community than Gerrit |
| Excellent screenshot annotation for design reviews | Extension ecosystem is modest |
| Easy to install and configure | Less suited for high-frequency, large-team workflows |

---

## Phorge: The Comprehensive Development Platform

Phorge is the community-maintained successor to Phabricator, the all-in-one development platform originally created by Facebook. When Phacility discontinued Phabricator in 2021, the community forked it and continued development as Phorge. It bundles code review (called **Differential**) alongside task management (Maniphest), repository hosting (Diffusion), wiki (Phriction), and more.

### Core Philosophy

Phorge is not just a code review tool — it is a complete development workspace. The philosophy is that code review should be tightly integrated with tasks, documentation, and repository browsing, all within a single interface. Changesets (called "revisions") can be linked to tasks, and task descriptions can reference specific lines of code.

### Core Features

- **Differential** — code review with inline comments, revision history, and Herald automation rules
- **Maniphest** — task tracking with custom fields, priorities, and subtasks
- **Diffusion** — repository browsing with blame, history, and branch/tag views
- **Phriction** — wiki for project documentation
- **Herald** — rule engine for automated actions (e.g., auto-assign reviewers based on file paths)
- **Harbormaster** — build and CI orchestration (can trigger external CI jobs)
- **Phrequent** — time tracking
- Arcanist CLI tool for posting revisions from the terminal
- Comprehensive REST and Conduit APIs
- Dark mode in the web interface

### Installation with Docker Compose

Phorge requires a more complex stack — PHP, a web server, MySQL/MariaDB, and optionally Phabricator daemons for background tasks:

```yaml
# docker-compose.yml
version: "3.8"

services:
  phorge:
    image: bolcom/phorge:latest
    container_name: phorge
    restart: unless-stopped
    ports:
      - "8080:80"
      - "2222:22"   # SSH for Arcanist
    environment:
      - PHORGE_HOST=phorge.example.com
      - PHORGE_ADMIN_USER=admin
      - PHORGE_ADMIN_PASSWORD=SecurePass2026!
      - PHORGE_ADMIN_EMAIL=admin@example.com
      - MYSQL_HOST=db
      - MYSQL_USER=phorge
      - MYSQL_PASSWORD=PhorgePass2026!
      - MYSQL_DATABASE=phorge
    volumes:
      - phorge_data:/srv/phorge/data
      - phorge_repos:/srv/phorge/repos
    depends_on:
      - db
    networks:
      - review-net

  db:
    image: mariadb:11.4
    container_name: phorge-db
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD=RootPass2026!
      - MYSQL_DATABASE=phorge
      - MYSQL_USER=phorge
      - MYSQL_PASSWORD=PhorgePass2026!
    volumes:
      - mariadb_data:/var/lib/mysql
    networks:
      - review-net

volumes:
  phorge_data:
  phorge_repos:
  mariadb_data:

networks:
  review-net:
    driver: bridge
```

After the stack is running, install the Arcanist CLI:

```bash
# Clone Arcanist and libphutil
cd /opt
git clone https://github.com/phacility/libphutil.git
git clone https://github.com/phorge-org/arcanist.git

# Add to PATH
echo 'export PATH="$PATH:/opt/arcanist/bin"' >> ~/.bashrc
source ~/.bashrc

# Configure Arcanist in your project
cd /path/to/your/project
cat > .arcconfig << 'EOF'
{
  "phabricator.uri": "http://phorge.example.com"
}
EOF

# Authenticate
arc install-certificate
# This opens the browser to confirm the API token

# Create and post a revision
arc diff
```

### Review Workflow (Differential)

1. A developer creates a branch and runs `arc diff`. Arcanist generates a diff, posts it to Phorge, and creates a **Differential Revision**.

2. Reviewers examine the diff in the web UI, leave inline comments, and use the "Accept Revision" or "Request Changes" actions.

3. Herald rules can automatically assign reviewers based on file paths, project membership, or custom rules.

4. Once accepted, the developer lands the changes using `arc land`, which merges the branch and closes the revision.

5. The revision can be linked to a Maniphest task, making it easy to trace which code changes addressed which requirements.

### Pros and Cons

| Pros | Cons |
|------|------|
| All-in-one platform — review, tasks, wiki, repos | Heavy stack — requires more resources and maintenance |
| Powerful Herald automation engine | Community is smaller than Gerrit's |
| Arcanist CLI is mature and feature-rich | PHP-based — some teams prefer other stacks |
| Tight integration between reviews and tasks | Fork history creates some uncertainty about long-term support |
| Excellent for teams wanting a unified dev workspace | Overkill if you only need code review |

---

## Head-to-Head Comparison

| Feature | Gerrit | Review Board | Phorge (Differential) |
|---------|--------|--------------|------------------------|
| **Primary VCS** | Git only | Git, SVN, Hg, Perforce, CVS | Git, SVN, Hg |
| **Review Model** | Patch sets | Review requests | Differential revisions |
| **Inline Comments** | Yes (threaded) | Yes (per-line) | Yes (inline + general) |
| **Merge Capability** | Built-in (multiple strategies) | No (external) | Yes (`arc land`) |
| **CI Integration** | Verified label + webhooks | Email + webhooks | Harbormaster + webhooks |
| **Authentication** | LDAP, OAuth, HTTP, SSH | LDAP, OAuth, AD, LDAP | LDAP, OAuth, SSO |
| **API** | REST + stream-events | REST + Python bindings | Conduit (REST-like) |
| **CLI Tool** | `git push` (native) | RBTools (`rbt`) | Arcanist (`arc`) |
| **Language** | Java | Python (Django) | PHP |
| **Min. RAM** | 2 GB | 512 MB | 1 GB |
| **Task Tracking** | No | No | Yes (Maniphest) |
| **Wiki** | No (plugin) | No | Yes (Phriction) |
| **Automation Rules** | Plugins | Limited | Yes (Herald) |
| **License** | Apache 2.0 | MIT | Apache 2.0 (Phorge) |
| **Active Development** | Very active | Active | Active (community) |

## Choosing the Right Platform

The decision comes down to your team's workflow, technical stack, and growth trajectory:

**Choose Gerrit if:**

- Your team works primarily with Git and values a strict, commit-level review process
- You have a large contributor base (50+ developers) where the patch-set model prevents merge conflicts
- You need fine-grained submit strategies and mandatory approval workflows
- You want a battle-tested platform backed by a large community and extensive plugin ecosystem
- Java infrastructure is not a concern for your team

**Choose Review Board if:**

- Your organization uses multiple version control systems or maintains legacy SVN/Perforce repositories
- You want a lightweight, easy-to-install review system that gets developers productive quickly
- Your team includes designers who benefit from screenshot annotation features
- You prefer Python/Django and want a platform that is straightforward to customize
- You need a simple approval workflow without the complexity of score-based gating

**Choose Phorge if:**

- Your team wants a unified workspace combining code review, task tracking, wikis, and repository browsing
- You value Herald's rule engine for automating reviewer assignment and policy enforcement
- You want tight integration between code changes and project tasks
- Your team is comfortable with PHP-based infrastructure
- You prefer the Arcanist CLI workflow and `arc land` for streamlined merges

## Production Hardening Checklist

Regardless of which platform you choose, these steps should be part of any production deployment:

```bash
# 1. Always put a reverse proxy in front (Caddy example)
cat > Caddyfile << 'EOF'
review.example.com {
    reverse_proxy localhost:8080
    encode gzip
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
    }
}
EOF

# 2. Set up automated backups
# For PostgreSQL-based platforms:
pg_dump -h db -U rbuser reviewboard > /backup/reviewboard-$(date +%Y%m%d).sql

# For Gerrit (H2 database):
docker cp gerrit:/var/gerrit/review_site/db/ReviewDB /backup/gerrit-h2-$(date +%Y%m%d)

# For MariaDB (Phorge):
mysqldump -h db -u phorge -p'PhorgePass2026!' phorge > /backup/phorge-$(date +%Y%m%d).sql

# 3. Monitor with health checks
# Add to docker-compose:
#   healthcheck:
#     test: ["CMD", "curl", "-f", "http://localhost:8080"]
#     interval: 30s
#     timeout: 10s
#     retries: 3

# 4. Configure email notifications
# All three platforms support SMTP. Example:
#   mail.smtp.host = smtp.example.com
#   mail.smtp.port = 587
#   mail.smtp.user = noreply@example.com
#   mail.smtp.password = SmtpPass2026!
```

## Conclusion

The best self-hosted code review platform is the one that matches your team's workflow, technical preferences, and growth plans. Gerrit excels in high-volume Git environments with strict governance requirements. Review Board shines in heterogeneous VCS environments where simplicity and speed matter. Phorge delivers the most comprehensive all-in-one experience for teams that want review, tasks, and documentation under one roof.

All three are mature, open-source, and production-ready. You cannot make a bad choice — the real question is which philosophy aligns with how your team works today and how it will scale tomorrow.
