---
title: "SpiderFoot vs theHarvester vs Recon-ng: Self-Hosted OSINT Frameworks Guide 2026"
date: 2026-04-29
tags: ["comparison", "guide", "self-hosted", "security", "osint", "reconnaissance"]
draft: false
description: "Compare three leading self-hosted OSINT frameworks — SpiderFoot, theHarvester, and Recon-ng — with Docker deployment guides, feature comparisons, and practical reconnaissance workflows."
---

Open-source intelligence (OSINT) gathering is a foundational skill for security teams, penetration testers, and system administrators. Whether you are mapping your organization's external attack surface, gathering intelligence for a red team engagement, or simply auditing what information about your infrastructure is publicly visible, having a self-hosted OSINT framework gives you full control over your reconnaissance data.

In this guide, we compare three of the most popular self-hosted OSINT frameworks — **SpiderFoot**, **theHarvester**, and **Recon-ng** — and show you how to deploy each one with Docker.

## Why Self-Host Your OSINT Framework

Running OSINT tools on your own infrastructure offers several advantages over cloud-based or SaaS alternatives:

- **Data privacy**: Reconnaissance results often contain sensitive findings about your infrastructure. Keeping data on-premises ensures it never leaves your network.
- **No rate limits or API quotas**: Self-hosted tools run on your schedule. You are not constrained by per-request limits or subscription tiers.
- **Custom module development**: Open-source frameworks let you write custom reconnaissance modules tailored to your specific environment or target infrastructure.
- **Full audit trail**: Every scan, query, and result is stored locally, giving you a complete historical record for compliance and incident investigation.
- **Cost**: All three tools covered in this guide are completely free and open-source, with no licensing fees regardless of how intensively you use them.

For organizations that combine OSINT with other security workflows — such as [network scanning](../2026-04-22-nmap-vs-masscan-vs-rustscan-self-hosted-network-scanning-guide-2026/) or [threat modeling](../2026-04-24-owasp-threat-dragon-vs-threatmap-vs-threatsea-self-hosted-threat-modeling-guide-2026/) — having these tools self-hosted makes it easier to build integrated security pipelines.

## SpiderFoot: Automated Attack Surface Mapping

**GitHub**: [smicallef/spiderfoot](https://github.com/smicallef/spiderfoot) — 17,595 stars
**Last updated**: April 2026
**Language**: Python

SpiderFoot is a comprehensive OSINT automation platform that queries over 200 public data sources to gather intelligence about IP addresses, domain names, email addresses, and usernames. Its standout feature is a full web-based user interface that visualizes relationships between discovered entities as an interactive graph.

### Key Features

- **200+ modules** covering DNS, WHOIS, threat intelligence feeds, social media, paste sites, and more
- **Web UI** with interactive entity graph visualization
- **API-first design** for automation and integration with other security tools
- **Scan targeting**: IP address, domain name, email, person name, autonomous system number, network subnet, and username
- **Correlation engine** automatically links related entities across data sources
- **Export formats**: CSV, GEXF (for Gephi), JSON, and HTML reports
- **Docker support** with official compose file and persistent data volume

SpiderFoot is ideal for teams that need a point-and-click OSINT interface with automated correlation. You define a target, start a scan, and the platform discovers related entities across hundreds of sources.

### Docker Compose Deployment

SpiderFoot provides an official Docker Compose configuration. The service exposes its web interface on port 5001 and stores all scan data in a persistent Docker volume:

```yaml
version: "3"

services:
  spiderfoot:
    build:
      context: ./
    volumes:
      - spiderfoot-data:/var/lib/spiderfoot
    image: spiderfoot
    container_name: spiderfoot
    ports:
      - "5001:5001"
    restart: unless-stopped

volumes:
  spiderfoot-data:
```

To get started:

```bash
# Clone the repository
git clone https://github.com/smicallef/spiderfoot.git
cd spiderfoot

# Start the web interface
docker-compose up -d

# Access the UI at http://localhost:5001
```

For the full image with all optional CLI tools installed, use the multi-file compose override:

```bash
docker-compose -f docker-compose.yml -f docker-compose-full.yml up -d
```

## theHarvester: Rapid Email and Subdomain Discovery

**GitHub**: [laramies/theHarvester](https://github.com/laramies/theHarvester) — 16,107 stars
**Last updated**: April 2026
**Language**: Python

theHarvester is a lightweight, fast reconnaissance tool focused on harvesting emails, subdomains, hostnames, employee names, open ports, and banners from public sources. It is designed to be run from the command line and produces clean, structured output that feeds directly into downstream tools.

### Key Features

- **Fast enumeration**: Optimized for speed, theHarvester can query dozens of sources in seconds
- **Source variety**: Search engines (Google, Bing, DuckDuckGo), certificate transparency logs, Shodan, Censys, Hunter.io, and more
- **API key support**: Integrates with premium data sources like SecurityTrails, Hunter.io, and ZoomEye when API keys are provided
- **DNS resolution**: Built-in DNS brute-forcing and virtual host discovery
- **Shodan integration**: Direct Shodan queries for open ports and service banners
- **Output formats**: JSON, CSV, and HTML reports
- **API configuration**: YAML-based API key management for optional data sources

theHarvester excels at quick, targeted reconnaissance. If you need a fast answer to "what emails and subdomains are publicly associated with this domain?", it is the fastest tool for the job.

### Docker Compose Deployment

theHarvester's Docker setup maps API key and proxy configuration files into the container, making it easy to customize without rebuilding the image:

```yaml
services:
  theharvester.svc.local:
    container_name: theHarvester
    volumes:
      - ./theHarvester/data/api-keys.yaml:/root/.theHarvester/api-keys.yaml
      - ./theHarvester/data/api-keys.yaml:/etc/theHarvester/api-keys.yaml
      - ./theHarvester/data/proxies.yaml:/etc/theHarvester/proxies.yaml
      - ./theHarvester/data/proxies.yaml:/root/.theHarvester/proxies.yaml
    build: .
    ports:
      - "5000:80"

networks:
  default:
    name: app_theHarvester_network
```

Basic usage:

```bash
# Clone and configure
git clone https://github.com/laramies/theHarvester.git
cd theHarvester

# (Optional) Add API keys for enhanced results
cp data/api-keys.yaml.example data/api-keys.yaml
# Edit api-keys.yaml with your credentials

# Build and run
docker-compose up -d

# Run a basic enumeration
docker exec -it theHarvester python3 theHarvester.py -d example.com -b all
```

Example API keys configuration:

```yaml
# data/api-keys.yaml
securitytrails: []
hunter: []
shodan: []
zoomeye: []
censys: []
```

## Recon-ng: Modular Reconnaissance Framework

**GitHub**: [lanmaster53/recon-ng](https://github.com/lanmaster53/recon-ng) — 5,543 stars
**Last updated**: November 2024
**Language**: Python

Recon-ng is a full-featured reconnaissance framework modeled after the Metasploit Framework. It provides a structured, modular approach to OSINT gathering with a command-line interface that supports workspaces, database storage, and a marketplace of additional modules.

### Key Features

- **Modular architecture**: Recon-ng is built around modules — discrete units of reconnaissance functionality that can be chained together
- **Workspace management**: Keep reconnaissance data for different targets isolated in separate workspaces
- **Built-in database**: All results are stored in a SQLite database, enabling complex queries and cross-referencing between modules
- **Marketplace**: Additional modules available through the built-in marketplace system
- **Reporting modules**: Generate HTML, CSV, and XML reports from collected data
- **Recon-web**: Optional web interface for visualizing and managing reconnaissance results
- **Worker queue**: Redis-backed task queue for asynchronous module execution
- **Auto-completion**: Tab-completion for modules, options, and commands

Recon-ng is the most structured and methodical of the three tools. Its workspace and database approach makes it ideal for longer engagements where you need to organize findings across multiple targets and phases of reconnaissance.

### Docker Compose Deployment

Recon-ng's Docker Compose configuration includes a web interface, a background worker, and a Redis instance for task queuing:

```yaml
version: '3.7'

services:
  web:
    build: .
    image: recon-ng
    container_name: recon-ng
    ports:
      - '5000:5000'
    command: python3 ./recon-web --host 0.0.0.0
    volumes:
      - .:/recon-ng
      - ~/.recon-ng:/root/.recon-ng
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis

  worker:
    image: recon-ng
    command: rq worker -u redis://redis:6379/0 recon-tasks
    volumes:
      - .:/recon-ng
      - ~/.recon-ng:/root/.recon-ng
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
      - web

  redis:
    image: redis
```

To deploy and use:

```bash
# Clone the framework
git clone https://github.com/lanmaster53/recon-ng.git
cd recon-ng

# Start all services (web UI, worker, Redis)
docker-compose up -d

# Access the web interface at http://localhost:5000
# Or use the CLI directly:
docker exec -it recon-ng ./recon-ng
```

Example Recon-ng workflow:

```
# Inside the Recon-ng CLI
[recon-ng][default] > workspaces create target-company
[recon-ng][target-company] > marketplace search
[recon-ng][target-company] > modules load recon/domains-hosts/bing_domain_web
[recon-ng][target-company][bing_domain_web] > set SOURCE example.com
[recon-ng][target-company][bing_domain_web] > run
[recon-ng][target-company][bing_domain_web] > show hosts
```

## Feature Comparison

| Feature | SpiderFoot | theHarvester | Recon-ng |
|---------|-----------|-------------|----------|
| **Web UI** | Full interactive UI with entity graph | Limited (CLI-focused) | Optional recon-web interface |
| **Modules/Sources** | 200+ modules | 30+ data sources | 60+ modules via marketplace |
| **Data Correlation** | Automatic entity correlation | No correlation | Manual via database queries |
| **API Integration** | Built-in REST API | API key config file | API keys per module |
| **Database Storage** | SQLite (persistent volume) | File-based output (JSON/CSV) | SQLite workspace database |
| **Docker Support** | Official compose | Official compose | Official compose with Redis |
| **Scan Automation** | Fully automated scans | Manual per-target runs | Semi-automated via workflows |
| **Target Types** | IP, domain, email, AS, subnet, person | Domain, company name | Domain, email, username, more |
| **Reporting** | HTML, CSV, GEXF, JSON | HTML, CSV, JSON | HTML, CSV, XML |
| **Active Development** | Very active (17.5K stars) | Active (16.1K stars) | Moderate (5.5K stars) |
| **Learning Curve** | Low (point and click) | Low (single command) | Moderate (framework concepts) |
| **Best For** | Attack surface mapping | Quick email/subdomain discovery | Structured reconnaissance |

## Which Tool Should You Choose?

### Choose SpiderFoot If:
- You want a visual, web-based OSINT platform with minimal setup
- Automatic entity correlation is important to your workflow
- You need to integrate OSINT results into other tools via its REST API
- Your team prefers point-and-click interfaces over command-line tools

### Choose theHarvester If:
- Speed is your top priority — you need answers in seconds
- Your primary need is email and subdomain enumeration
- You want to pipe results directly into other CLI tools
- You prefer lightweight tools with minimal dependencies

### Choose Recon-ng If:
- You need structured, workspace-based reconnaissance
- You run longer engagements that require organized findings
- You want the flexibility of a modular framework (similar to Metasploit)
- You need database-backed storage with cross-module queries

Many professional security teams run **all three tools** in combination: theHarvester for quick initial enumeration, SpiderFoot for comprehensive automated scanning, and Recon-ng for structured, multi-phase reconnaissance campaigns. Results from each tool feed into [vulnerability management platforms](../2026-04-20-defectdojo-vs-greenbone-vs-faraday-self-hosted-vulnerability-management-2026/) for further analysis.

## Running All Three with Docker Compose

For teams that want all three tools available on a single reconnaissance server, here is a combined Docker Compose file:

```yaml
version: "3.8"

services:
  spiderfoot:
    image: spiderfoot
    container_name: spiderfoot
    ports:
      - "5001:5001"
    volumes:
      - spiderfoot-data:/var/lib/spiderfoot
    restart: unless-stopped

  theharvester:
    build:
      context: ./theHarvester
    container_name: theHarvester
    ports:
      - "5002:80"
    volumes:
      - ./theHarvester/data:/root/.theHarvester/data
    restart: unless-stopped

  recon-ng-web:
    build:
      context: ./recon-ng
    container_name: recon-ng-web
    ports:
      - "5003:5000"
    volumes:
      - ./recon-ng:/recon-ng
    environment:
      - REDIS_URL=redis://recon-redis:6379/0
    depends_on:
      - recon-redis
    restart: unless-stopped

  recon-redis:
    image: redis:7-alpine
    container_name: recon-redis
    restart: unless-stopped

volumes:
  spiderfoot-data:
```

Start the full reconnaissance stack:

```bash
docker-compose -f docker-compose-osint.yml up -d

# Access each tool:
# SpiderFoot:    http://localhost:5001
# theHarvester:  http://localhost:5002
# Recon-ng Web:  http://localhost:5003
```

## FAQ

### What is OSINT and why is it important for security?

OSINT (Open-Source Intelligence) refers to the collection and analysis of information from publicly available sources. For security teams, OSINT reveals what an attacker can discover about your organization without any direct access — including exposed subdomains, employee emails, leaked credentials, and infrastructure details. Running OSINT proactively helps you identify and remediate exposures before malicious actors find them.

### Is it legal to run OSINT against my own organization?

Yes, gathering publicly available information about your own organization's infrastructure is legal and is considered a standard security practice. However, running OSINT against organizations you do not own or have explicit permission to test may violate local laws or terms of service. Always ensure you have proper authorization before conducting reconnaissance activities.

### Can these tools be used for bug bounty programs?

Absolutely. All three tools are widely used in bug bounty programs for the initial reconnaissance phase. SpiderFoot's automated scanning, theHarvester's quick subdomain enumeration, and Recon-ng's modular approach all help bug hunters identify potential targets and attack surfaces. Results often feed into further testing with tools like [network scanners](../2026-04-22-nmap-vs-masscan-vs-rustscan-self-hosted-network-scanning-guide-2026/).

### How do I add API keys to enhance OSINT results?

Each tool handles API keys differently:
- **SpiderFoot**: Configure API keys through the web UI under Settings > API Keys for each module
- **theHarvester**: Edit the `data/api-keys.yaml` file with your credentials for sources like Shodan, Hunter.io, and SecurityTrails
- **Recon-ng**: Use the `keys` command within the CLI to set API keys per module (e.g., `keys add shodan_api YOUR_KEY`)

### How often should I run OSINT scans against my infrastructure?

For most organizations, running a full OSINT scan monthly is a good baseline. High-change environments (frequent deployments, new acquisitions) may benefit from weekly scans. SpiderFoot's API makes it easy to automate recurring scans via cron jobs or CI/CD pipelines, while theHarvester's CLI interface integrates well with automated security testing pipelines.

### Do these tools perform active scanning or only passive reconnaissance?

All three tools focus on **passive reconnaissance** — they query public data sources and search engines rather than actively probing your infrastructure. This means they will not trigger intrusion detection systems or generate network traffic to your servers. However, some modules (like DNS brute-forcing in theHarvester) do generate network queries that may be logged by your DNS provider.

## OSINT Data Sources Used by These Tools

| Data Source | SpiderFoot | theHarvester | Recon-ng |
|-------------|-----------|-------------|----------|
| Search Engines | Google, Bing, DuckDuckGo | Google, Bing, DuckDuckGo, Yahoo | Google, Bing |
| Certificate Transparency | crt.sh, Censys | Censys | crt.sh |
| DNS Records | Multiple DNS modules | Built-in resolution | Multiple DNS modules |
| WHOIS | Built-in | Limited | Built-in |
| Social Media | LinkedIn, Twitter, Facebook | Twitter, LinkedIn | LinkedIn |
| Threat Intelligence | Multiple threat feeds | Shodan, Censys | Multiple modules |
| Code Repositories | GitHub, GitLab | GitHub | GitHub |
| Paste Sites | Pastebin, Ghostbin | Pastebin | Pastebin |
| Email Harvesting | 20+ modules | 15+ sources | 10+ modules |

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "SpiderFoot vs theHarvester vs Recon-ng: Self-Hosted OSINT Frameworks Guide 2026",
  "description": "Compare three leading self-hosted OSINT frameworks — SpiderFoot, theHarvester, and Recon-ng — with Docker deployment guides, feature comparisons, and practical reconnaissance workflows.",
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
