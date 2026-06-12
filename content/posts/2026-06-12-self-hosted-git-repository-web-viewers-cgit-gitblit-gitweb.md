---
title: "Self-Hosted Git Repository Web Viewers: cgit vs Gitblit vs gitweb"
date: "2026-06-12"
tags: ["git", "developer-tools", "self-hosted-server", "code-hosting", "web-interface", "version-control", "repository-management"]
draft: false
---

## Introduction

Not every project needs a full-featured Git forge like GitLab or Gitea. Sometimes you just want to browse repositories through a web browser — view commits, inspect files, check branches, and read READMEs — without the overhead of issue trackers, pull requests, CI/CD pipelines, and user management.

This is where lightweight Git web viewers shine. **cgit** (used by kernel.org and git.kernel.org to serve the Linux kernel), **Gitblit** (a self-contained Java WAR with built-in repository management), and **gitweb** (the Perl CGI script that ships with Git itself) each provide fast, efficient repository browsing. They consume minimal resources and can serve hundreds of repositories on a $5 VPS.

## Comparison Table

| Feature | cgit | Gitblit | gitweb |
|---------|------|---------|--------|
| **Language** | C | Java | Perl |
| **Deployment** | FastCGI behind Nginx/Apache | Standalone WAR or Tomcat | CGI behind any web server |
| **Repository Discovery** | Scan filesystem path | Built-in repo manager or filesystem scan | Scan filesystem path |
| **Built-in Git Server** | No (read-only) | Yes (Git Daemon + HTTP/HTTPS) | No (read-only) |
| **Authentication** | Via web server (HTTP Basic, LDAP) | Built-in (LDAP, file, Redmine, etc.) | Via web server |
| **Repository Management** | None (scan-only) | Web UI for create/edit/delete repos | None (scan-only) |
| **Markdown Rendering** | Via about filter (shell script) | Built-in Markdown/Textile/Confluence | None |
| **Clone URLs** | Display only | Full HTTP/HTTPS/Git Daemon clone support | Display only |
| **Performance** | Extremely fast (C, mmap) | Good (Java, caching) | Moderate (CGI per-request) |
| **GitHub Stars** | N/A (email-based dev) | 2,352+ | Part of git.git |
| **RSS/Atom Feeds** | Yes per repository | No (planned) | Yes |
| **Best For** | High-performance public mirrors | All-in-one small team server | Minimal setup, part of Git |

## cgit

cgit is a hyper-fast Git web interface written in C. It powers some of the highest-traffic Git browsers on the internet, including `git.kernel.org` (serving the Linux kernel repository to thousands of concurrent developers). cgit is read-only — it displays repositories beautifully but does not manage them or handle pushes.

Its speed comes from aggressive caching and direct use of libgit2 for repository operations. Page generation is measured in microseconds, not milliseconds. The UI is clean and information-dense: commit logs, tree views, diffs with syntax highlighting, blame annotations, and per-repository Atom feeds.

```nginx
# Nginx configuration for cgit via FastCGI
server {
    listen 80;
    server_name git.example.com;

    root /var/www/cgit;
    
    location / {
        try_files $uri @cgit;
    }

    location @cgit {
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME /usr/lib/cgit/cgit.cgi;
        fastcgi_param PATH_INFO $uri;
        fastcgi_param QUERY_STRING $query_string;
        fastcgi_pass unix:/run/fcgiwrap.socket;
    }
}
```

cgit configuration lives in `/etc/cgitrc`:

```ini
# /etc/cgitrc
cache-size=1000
cache-root=/var/cache/cgit
css=/cgit.css
logo=/cgit.png
root-title=My Git Repositories
root-desc=Open source projects
snapshots=tar.gz tar.bz2 zip

# Enable Markdown about pages
about-filter=/usr/lib/cgit/filters/about-formatting.sh

# Source code syntax highlighting
source-filter=/usr/lib/cgit/filters/syntax-highlighting.sh

# Scan for repositories
scan-path=/srv/git/

# Per-repo overrides
repo.url=my-project
repo.path=/srv/git/my-project.git
repo.desc=An example project
repo.owner=Jane Developer
```

## Gitblit

Gitblit takes the opposite approach from cgit: it's a self-contained Java application that bundles repository browsing, Git hosting, access control, and repository management into a single WAR file. Deploy it with `java -jar gitblit.jar` and you get a fully functional Git server with a polished web interface.

Unlike cgit's scan-only model, Gitblit includes a web-based repository manager. Create, rename, and delete repositories through the browser. Set per-repository access permissions. Configure federation to mirror repositories between Gitblit instances. Gitblit also bundles a Git daemon and HTTP/HTTPS Git transport, making it both a viewer and a Git server.

```yaml
# docker-compose.yml for Gitblit
version: '3.8'
services:
  gitblit:
    image: gitblit/gitblit:latest
    ports:
      - "8080:8080"    # Web UI
      - "8443:8443"    # HTTPS
      - "9418:9418"    # Git daemon
      - "29418:29418"  # SSH
    volumes:
      - ./gitblit-data:/opt/gitblit-data
    environment:
      - JAVA_OPTS=-Xmx512m -server
    restart: unless-stopped
```

Gitblit's access control is notably flexible for a lightweight tool. It supports multiple authentication backends: a built-in file-based user store, LDAP, Redmine, and more. Teams can be granted fine-grained permissions (view, clone, push, create refs, delete refs, rewind) per repository.

## gitweb

gitweb is the original Git web viewer — it ships with Git itself and has been browsing repositories since 2005. Written in Perl as a CGI script, it's the lowest-friction option: if you have Git installed, you already have gitweb.

Its interface is dated by modern standards, but it gets the job done: repository listing, commit logs, tree browsing, blame, diffs, and snapshot downloads (tar.gz, zip). Configuration is minimal — just point it at your repository directory.

```apache
# Apache configuration for gitweb
<VirtualHost *:80>
    ServerName git.example.com
    DocumentRoot /usr/share/gitweb

    <Directory /usr/share/gitweb>
        Options +ExecCGI +FollowSymLinks
        AddHandler cgi-script .cgi
        DirectoryIndex gitweb.cgi
    </Directory>

    SetEnv GITWEB_PROJECTROOT /srv/git
</VirtualHost>
```

For a more modern feel, install gitweb-theme from GitHub to replace the 2005-era default CSS with something that looks like it belongs in this decade.

## Choosing the Right Tool

| Use Case | Recommended Tool |
|----------|-----------------|
| Public mirror of 500+ repos, kernel.org scale | cgit |
| Small team needing repo management + access control | Gitblit |
| Quick setup with zero extra dependencies | gitweb |
| LDAP-integrated enterprise browsing | Gitblit |
| Maximum visual customization | cgit (CSS + filters) |
| Push/pull hosting included | Gitblit |
| CI/CD integration (post-receive hooks) | Gitblit or cgit |

## Why Self-Host Your Git Repository Viewer?

Running your own Git web viewer keeps your source code on your infrastructure. For organizations subject to data residency requirements (GDPR, HIPAA, ITAR), hosting repositories on US-based cloud platforms can create compliance headaches. A self-hosted viewer on a server in your data center eliminates this concern entirely.

Performance is another factor. Cloning a large repository through `git.example.com` on your local network saturates a gigabit link, while cloning through a cloud-hosted platform contends with internet bandwidth and rate limiting. For monorepos with hundreds of megabytes of history, local access is dramatically faster.

On the customization front, cgit's filter architecture lets you inject arbitrary processing into every page. Add custom headers, inject analytics, transform Markdown through Pandoc, or run source code through custom syntax highlighters — capabilities that SaaS platforms gate behind enterprise pricing tiers.

For related Git infrastructure tools, see our comparison of [self-hosted Git forges (Gitea, Forgejo, GitLab CE)](../gitea-vs-forgejo-vs-gitlab-ce-self-hosted-git-forge/) and our guide to [lightweight Git hosting platforms](../2026-04-26-gogs-vs-gitbucket-vs-onedev-lightweight-self-hosted-git-platforms-2026/). If you need to visualize commit history, our [Git history visualization guide](../2026-05-05-self-hosted-git-history-visualization-pomber-gource-gitgraph-guide/) covers Gource and related tools.

## Repository Layout and Discovery Strategies

How you organize repositories on disk directly affects the browsing experience. All three viewers support scanning a directory tree, but they handle nested groups differently. cgit renders nested directories as path-based groups (e.g., `/srv/git/team/project.git` appears under "team/project"), creating a natural namespace hierarchy. Gitblit uses a flat project structure with optional project grouping. gitweb displays everything in a single flat list.

For organizations with hundreds of repositories, cgit's hierarchical approach is invaluable. Structure your filesystem like `organization/team/project.git` and cgit automatically generates breadcrumb navigation. This makes finding repositories intuitive — a developer looking for the authentication service navigates to `platform/auth-service` rather than scrolling through an alphabetical list of 500 repos.

Repository description and owner metadata matter for discoverability. cgit reads the `description` file inside each bare repository and the owner from git config. Gitblit stores metadata in its own database with a web UI for editing. gitweb also reads the `description` file and supports an `owner` file. For teams adopting any of these viewers, establish a convention for keeping repository descriptions current — stale descriptions are the most common cause of "I can't find the repo" support tickets.

Large binary repositories (game assets, design files, scientific datasets) present a different challenge. cgit handles large repos gracefully through mmap-based access, but generating tar.gz snapshots of multi-gigabyte repositories can overwhelm the server. Configure snapshot size limits or disable snapshot generation for repos exceeding a threshold. Gitblit's built-in Git hosting means clones are served directly without the snapshot overhead.


## FAQ

### Can cgit or gitweb handle repository push operations?

No. Both cgit and gitweb are read-only viewers. They display repository contents through a web browser but do not accept `git push` operations. You'll need a separate Git server (git-daemon, git-http-backend via Nginx/Apache, or SSH access) to handle writes. Gitblit is the only option here that bundles read-write Git hosting with its web viewer.

### How do these compare to Gitea or GitLab's built-in repository browser?

Gitea and GitLab include repository browsing as one feature among many. If you're already running Gitea/GitLab, their built-in browsers are perfectly adequate. cgit and gitweb are for situations where you want repository browsing *without* the full forge overhead — public mirrors, read-only archives, or hosting repositories that are pushed to through SSH/Git protocol but browsed through a separate lightweight interface.

### Can I add syntax highlighting to cgit?

Yes. cgit supports a `source-filter` directive that pipes source files through an external program. The standard approach uses `highlight` or `pygmentize`:

```ini
source-filter=/usr/lib/cgit/filters/syntax-highlighting.sh
```

The included filter script (`syntax-highlighting.sh`) detects language from file extensions and applies appropriate highlighting. Custom filters can use any command-line tool that reads stdin and writes HTML to stdout.

### What's the performance difference between cgit and Gitblit?

cgit is substantially faster. Written in C and using libgit2 for direct memory-mapped repository access, page generation times are typically under 10ms even for large repositories. Gitblit runs on the JVM with caching and is fast enough for most use cases (10-100ms per page), but the architectural overhead of Java is real. For a public mirror serving hundreds of concurrent users, cgit is the clear performance winner.

### Can I run Gitblit behind a reverse proxy?

Yes. Gitblit listens on port 8080 (HTTP) and optionally 8443 (HTTPS). Deploy it behind Nginx, Caddy, or Apache with standard reverse proxy configuration for TLS termination and custom domain routing. Gitblit respects the `X-Forwarded-For` and `X-Forwarded-Proto` headers for correct URL generation behind proxies.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Git Repository Web Viewers: cgit vs Gitblit vs gitweb",
  "description": "Compare lightweight open-source Git web viewers: cgit (C, kernel.org-level performance), Gitblit (Java, built-in repo management), and gitweb (Perl, ships with Git). Includes Nginx/Apache config, Docker Compose, and guidance on choosing the right viewer.",
  "datePublished": "2026-06-12",
  "dateModified": "2026-06-12",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
