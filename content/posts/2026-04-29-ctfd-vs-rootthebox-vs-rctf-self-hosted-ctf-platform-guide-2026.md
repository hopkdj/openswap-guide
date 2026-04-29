---
title: "CTFd vs RootTheBox vs rCTF: Best Self-Hosted CTF Platform 2026"
date: 2026-04-29
tags: ["comparison", "guide", "self-hosted", "security", "education"]
draft: false
description: "Compare the top open-source CTF platforms — CTFd, RootTheBox, and rCTF — for building self-hosted Capture The Flag competitions. Includes Docker setup, feature comparison, and deployment guide."
---

Capture The Flag competitions have become the gold standard for hands-on cybersecurity training. Whether you are running a classroom exercise, an internal team-building event, or a large-scale public competition, a dedicated CTF platform handles challenge deployment, flag submission, scoring, and real-time leaderboards.

Building your own platform on infrastructure you control means complete data ownership, custom branding, and the ability to integrate with internal authentication systems. In this guide, we compare three leading open-source CTF platforms — CTFd, RootTheBox, and rCTF — and walk through deploying each one with Docker.

## Why Self-Host a CTF Platform

Running a CTF on a third-party service works for small events, but self-hosting gives you capabilities that cloud platforms cannot match:

- **Full control over challenge infrastructure** — deploy vulnerable containers, file servers, and network services on your own infrastructure without external dependencies
- **Data privacy** — participant data, submission logs, and challenge solutions never leave your servers
- **Custom authentication** — integrate with LDAP, SAML, or OAuth providers for internal competitions
- **No participant limits** — scale to hundreds or thousands of players without per-user licensing fees
- **Persistent environment** — keep your platform running year-round for ongoing training, not just annual events
- **Offline capability** — run competitions in air-gapped environments or locations with limited internet connectivity

## CTFd

[CTFd](https://github.com/CTFd/CTFd) is the most widely adopted open-source CTF platform, with over 6,600 GitHub stars and more than 10 million Docker Hub pulls. It powers competitions at DEF CON qualifiers, university courses, and corporate security awareness programs worldwide.

### Architecture

CTFd runs as a Python Flask application backed by a MariaDB (or MySQL) database and Redis cache. The official Docker Compose stack includes an Nginx reverse proxy for static file serving and TLS termination.

### Features

- **Jeopardy-style challenges** — standard flag-based scoring with categories and point values
- **Dynamic scoring** — points decrease as more teams solve a challenge
- **Team mode** — players form teams with shared scores and team member management
- **File uploads** — attach downloadable challenge files directly to challenges
- **Page editor** — create custom informational pages with a built-in Markdown editor
- **Plugin system** — extend functionality with community plugins (themes, auth providers, scoring modules)
- **Import/Export** — migrate challenge bundles between instances using JSON archives
- **REST API** — programmatic access to challenges, submissions, and team data
- **Email integration** — user registration confirmation and password reset via SMTP

### Docker Compose Setup

```yaml
services:
  ctfd:
    image: ctfd/ctfd:latest
    restart: always
    ports:
      - "8000:8000"
    environment:
      - UPLOAD_FOLDER=/var/uploads
      - DATABASE_URL=mysql+pymysql://ctfd:ctfd_password@db/ctfd
      - REDIS_URL=redis://cache:6379
      - WORKERS=1
      - LOG_FOLDER=/var/log/CTFd
      - ACCESS_LOG=-
      - ERROR_LOG=-
      - REVERSE_PROXY=true
    volumes:
      - ctfd-data:/var/uploads
      - ctfd-logs:/var/log/CTFd
    depends_on:
      - db
      - cache

  nginx:
    image: nginx:stable
    restart: always
    volumes:
      - ./conf/nginx/http.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - ctfd

  db:
    image: mariadb:10.11
    restart: always
    environment:
      - MARIADB_ROOT_PASSWORD=root_password
      - MARIADB_USER=ctfd
      - MARIADB_PASSWORD=ctfd_password
      - MARIADB_DATABASE=ctfd
      - MARIADB_AUTO_UPGRADE=1
    volumes:
      - mysql-data:/var/lib/mysql
    command: [mysqld, --character-set-server=utf8mb4, --collation-server=utf8mb4_unicode_ci]

  cache:
    image: redis:7
    restart: always
    volumes:
      - redis-data:/data

volumes:
  ctfd-data:
  ctfd-logs:
  mysql-data:
  redis-data:
```

Deploy with:

```bash
mkdir -p conf/nginx
# Create your nginx config at conf/nginx/http.conf
docker compose up -d
```

CTFd's web UI is available at `http://<your-server>:80` after the first startup wizard completes.

### Limitations

- No built-in dynamic challenge containers — you need a separate plugin (like CTFd-Whale) to spin up per-team containers
- Scoring is limited to standard CTF models; advanced scoring requires custom plugins
- Default theme is functional but basic; custom themes require template editing

## RootTheBox

[RootTheBox](https://github.com/moloch--/RootTheBox) bills itself as "A Game of Hackers" and takes a more immersive approach than traditional CTF platforms. Instead of simple flag submissions, it models a corporate network where players attack boxes, capture flags, and earn money to purchase hints or attack other teams.

### Architecture

RootTheBox is built with Python and Tornado, using a simpler Memcached-based session store. The platform is designed around the "game board" metaphor — players navigate a corporate network map with boxes representing servers they need to compromise.

### Features

- **Corporate network simulation** — the game board mimics a real corporate IT environment with departments and server roles
- **Box-and-flag model** — each "box" (server) has multiple flags at increasing difficulty levels
- **In-game economy** — players earn money for captures and can spend it on hints, bribes, or attacks against other teams
- **Marketplace** — buy and sell exploits, flags, and power-ups between teams
- **Team warfare** — offensive actions against other teams (DDoS, stealing flags) add competitive depth
- **Hint system** — progressive hints with decreasing point rewards for each revealed clue
- **Screenshot proofs** — players upload screenshots as evidence for manual validation
- **Real-time leaderboards** — animated scoreboard with team ranking updates
- **Multi-language support** — interface available in several languages

### Docker Compose Setup

```yaml
services:
  memcached:
    image: memcached:latest
    ports:
      - "11211:11211"

  webapp:
    image: moloch/rootthebox:latest
    restart: always
    ports:
      - "8888:8888"
    volumes:
      - rtb-files:/opt/rtb/files:rw
    environment:
      - COMPOSE_CONVERT_WINDOWS_PATHS=1
    depends_on:
      - memcached

volumes:
  rtb-files:
```

Deploy with:

```bash
docker compose up -d
```

Access the platform at `http://<your-server>:8888`. The first-run configuration wizard lets you set up the admin account and competition parameters.

### Limitations

- Smaller community and fewer third-party plugins compared to CTFd
- The "game board" metaphor may not suit traditional jeopardy-style competitions
- Memcached-based storage lacks persistence guarantees — restarts can lose session data
- Less active development cad than CTFd, though still maintained

## rCTF

[rCTF](https://github.com/redpwn/rctf) is a lightweight, modern CTF platform built by the organizers of redpwnCTF, one of the largest student-run CTF competitions. It focuses on speed, simplicity, and a clean user experience.

### Architecture

rCTF is a Node.js application with a PostgreSQL database and Redis cache. The frontend is a React single-page application, and the platform uses an event-driven architecture for real-time scoreboard updates.

### Features

- **Modern web UI** — responsive React frontend with a clean, minimal design
- **Dynamic challenges** — built-in support for challenges whose point values change based on solve count
- **Real-time scoreboard** — WebSocket-based live updates without page refresh
- **Multi-instance support** — designed to run behind a load balancer for horizontal scaling
- **Challenge categories and tags** — organize challenges by type and difficulty
- **File hosting** — serve challenge attachments directly from the platform
- **Team-based competitions** — native support for team registration and scoring
- **API-first design** — comprehensive REST API for integrations and automation
- **Docker-native** — designed from the ground up for container deployment

### Docker Compose Setup

```yaml
services:
  rctf:
    image: redpwn/rctf:latest
    restart: always
    ports:
      - "127.0.0.1:8080:80"
    environment:
      - PORT=80
      - DATABASE_URL=postgres://rctf:rctf_password@postgres:5432/rctf
      - REDIS_URL=redis://:redis_password@redis:6379
      - ORIGIN=http://localhost:8080
      - REGISTRATION=true
    volumes:
      - ./conf.d:/app/conf.d
    depends_on:
      - redis
      - postgres

  redis:
    image: redis:7
    restart: always
    command: ["redis-server", "--requirepass", "redis_password"]
    volumes:
      - redis-data:/data

  postgres:
    image: postgres:15
    restart: always
    environment:
      - POSTGRES_PASSWORD=rctf_password
      - POSTGRES_USER=rctf
      - POSTGRES_DB=rctf
    volumes:
      - pg-data:/var/lib/postgresql/data

volumes:
  redis-data:
  pg-data:
```

Deploy with:

```bash
mkdir -p conf.d
docker compose up -d
```

The platform is available at `http://<your-server>:8080`. Note that rCTf binds to `127.0.0.1` by default — configure your reverse proxy or change the bind address for external access.

### Limitations

- Smaller project (272 GitHub stars) with less active development
- Fewer built-in challenge types compared to CTFd
- No plugin ecosystem — customization requires code changes
- Requires a reverse proxy (Nginx, Caddy) for TLS termination and external access

## Feature Comparison

| Feature | CTFd | RootTheBox | rCTF |
|---------|------|------------|------|
| **Language** | Python (Flask) | Python (Tornado) | Node.js (Express) |
| **Database** | MariaDB / MySQL | None (in-memory) | PostgreSQL |
| **Cache** | Redis | Memcached | Redis |
| **GitHub Stars** | 6,636 | 1,104 | 272 |
| **Docker Pulls** | 10M+ | N/A | N/A |
| **Dynamic Scoring** | Yes (plugin) | No (manual) | Built-in |
| **Team Mode** | Yes | Yes | Yes |
| **Plugin System** | Extensive | None | None |
| **REST API** | Yes | Limited | Yes |
| **Real-time UI** | Partial | Basic | Full (WebSocket) |
| **Custom Themes** | Yes (Jinja2) | Yes (Handlebars) | Yes (React) |
| **File Attachments** | Yes | Yes (screenshots) | Yes |
| **Hint System** | Yes (paid hints) | Yes (marketplace) | No |
| **Challenge Import** | JSON export/import | Manual | Manual |
| **Multi-instance** | Via Redis | No | Yes (designed for it) |
| **License** | Apache 2.0 | GPL-3.0 | MIT |

## Choosing the Right Platform

The best choice depends on your competition format and operational requirements:

**Choose CTFd if:**
- You want the most battle-tested platform with the largest community
- You need plugin extensibility for custom features
- You plan to reuse challenge bundles across multiple events
- Your team has Python/Flask experience for customization

**Choose RootTheBox if:**
- You want an immersive "game of hackers" experience
- Team-vs-team offensive actions are part of your competition design
- You value simplicity over feature breadth
- Your participants will enjoy the in-game economy and marketplace mechanics

**Choose rCTF if:**
- You need a lightweight, fast platform with real-time updates
- You are running a jeopardy-style CTF with many concurrent players
- Horizontal scaling behind a load balancer is a requirement
- Your team prefers the Node.js/PostgreSQL ecosystem

## Deployment Tips

Regardless of which platform you choose, follow these best practices for production deployment:

**1. Always use a reverse proxy** — place Nginx or Caddy in front of the CTF platform for TLS termination, rate limiting, and static file caching.

**2. Secure the database** — use strong passwords, restrict network access to the internal Docker network, and enable automated backups with a cron job:

```bash
# MariaDB backup (CTFd)
docker compose exec db mysqldump -u root -p ctfd > /backup/ctfd-$(date +%Y%m%d).sql

# PostgreSQL backup (rCTF)
docker compose exec postgres pg_dump -U rctf rctf > /backup/rctf-$(date +%Y%m%d).sql
```

**3. Configure rate limiting** — protect flag submission endpoints from brute-force attacks. With Nginx:

```nginx
limit_req_zone $binary_remote_addr zone=flag_submit:10m rate=5r/m;

location /api/v1/challenges/attempt {
    limit_req zone=flag_submit burst=3 nodelay;
    proxy_pass http://ctfd:8000;
}
```

**4. Monitor resource usage** — CTF competitions generate bursty traffic. Set up monitoring with tools like [Uptime Kuma](https://uptime.kuma.pet/) or [Gatus](https://github.com/TwiN/gatus) to detect platform degradation during peak competition hours.

**5. Prepare for scale** — test your deployment with simulated load before the event. Use tools like k6 or Locust to generate realistic submission patterns and identify bottlenecks in your stack.

**6. Complement your CTF with other security training tools** — pair your CTF platform with [phishing simulation tools](../self-hosted-phishing-simulation-security-awareness-training-gophish-2026/) for comprehensive security awareness, or integrate [malware analysis sandboxes](../cuckoo-sandbox-vs-capev2-vs-drakvuf-sandbox-self-hosted-malware-analysis-2026/) for advanced forensics challenges. For reconnaissance-themed challenges, consider incorporating [OSINT frameworks](../2026-04-29-spiderfoot-vs-theharvester-vs-recon-ng-self-hosted-osint-frameworks-guide-2026/) to teach information-gathering techniques.

## FAQ

### What is a CTF (Capture The Flag) competition?

A CTF is a cybersecurity competition where participants solve challenges to find hidden "flags" — strings of text that prove they have completed a task. Challenges typically cover categories like web exploitation, cryptography, reverse engineering, forensics, and binary exploitation. CTFs come in two main formats: jeopardy-style (independent challenges) and attack-defense (teams protect and attack live services).

### Can I run a CTF platform without Docker?

Yes. All three platforms support bare-metal installation. CTFd requires Python 3.8+, MariaDB/MySQL, and Redis. RootTheBox needs Python 3.x and Memcached. rCTF requires Node.js 16+, PostgreSQL, and Redis. However, Docker Compose is the recommended deployment method as it handles all dependencies in a single command and isolates the platform from your host system.

### How many participants can a self-hosted CTF platform handle?

CTFd has been tested with thousands of concurrent users and powers large public competitions. rCTF is designed for horizontal scaling with multi-instance support. RootTheBox is better suited for smaller events (under 200 participants) due to its in-memory architecture. For competitions exceeding 1,000 concurrent players, use a load balancer, multiple application instances, and a managed database.

### Can I integrate a self-hosted CTF with LDAP or SAML authentication?

CTFd supports custom authentication through its plugin system — several community plugins provide LDAP, SAML, and OAuth integration. RootTheBox and rCTF do not have built-in SSO support and would require custom code changes or a reverse proxy authentication layer (such as oauth2-proxy) to handle external authentication.

### How do I create dynamic challenges that spawn containers per player?

CTFd supports dynamic challenge containers through the CTFd-Whale plugin, which integrates with Docker or Kubernetes to spin up isolated environments for each player or team. rCTF and RootTheBox do not have built-in container orchestration — you would need to build a custom challenge deployment system or use an external framework like [Judge0](https://github.com/judge0/judge0) for code execution challenges.

### Is it legal to host a CTF with real vulnerability exploitation?

CTF challenges that simulate real-world vulnerabilities are legal when run in isolated, consented environments. The key is that all challenge infrastructure must be owned or authorized by the competition organizer, and participants must agree to the rules of engagement. Never include challenges that target third-party systems without explicit written permission.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "CTFd vs RootTheBox vs rCTF: Best Self-Hosted CTF Platform 2026",
  "description": "Compare the top open-source CTF platforms — CTFd, RootTheBox, and rCTF — for building self-hosted Capture The Flag competitions. Includes Docker setup, feature comparison, and deployment guide.",
  "datePublished": "2026-04-29",
  "dateModified": "2026-04-29",
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
