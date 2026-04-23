---
title: "Amass vs Subfinder vs MassDNS: Self-Hosted DNS Reconnaissance & Subdomain Enumeration Guide 2026"
date: 2026-04-23
tags: ["comparison", "guide", "self-hosted", "security", "dns", "reconnaissance"]
draft: false
description: "Compare OWASP Amass, ProjectDiscovery Subfinder, and MassDNS for self-hosted DNS reconnaissance and subdomain enumeration. Complete Docker deployment guide with configs, comparison tables, and best practices."
---

Subdomain enumeration and DNS reconnaissance are critical components of any security assessment, penetration testing workflow, or attack surface management strategy. Whether you are auditing your own infrastructure, monitoring for shadow IT, or preparing for a red team engagement, having reliable self-hosted DNS reconnaissance tools is essential.

Three open-source projects dominate this space: **OWASP Amass**, **ProjectDiscovery Subfinder**, and **MassDNS**. Each takes a fundamentally different approach to DNS enumeration, and understanding their strengths and weaknesses will help you choose the right tool — or better yet, combine them for comprehensive coverage.

For related reading, see our [OWASP ZAP vs Nuclei vs Nikto DAST scanning guide](../owasp-zap-vs-nuclei-vs-nikto-self-hosted-dast-scanning-guide-2026/) and [OpenVAS vs Trivy vs Grype vulnerability scanner guide](../openvas-trivy-grype-self-hosted-vulnerability-scanner-guide/).

## Why Self-Host DNS Reconnaissance Tools?

Running DNS enumeration tools on your own infrastructure offers several advantages over cloud-based scanners:

- **No rate limiting or API quotas** — self-hosted tools don't share resources with other users
- **Full control over data** — all discovered subdomains stay on your infrastructure
- **Automation and scheduling** — integrate with cron jobs, CI/CD pipelines, and security orchestration platforms
- **Custom wordlists and configurations** — tune enumeration to your specific domain structure
- **Cost-effective** — no per-scan or per-domain pricing models

A comprehensive DNS reconnaissance setup typically combines passive enumeration (querying public data sources) with active brute-forcing (testing wordlists against DNS resolvers). The three tools covered here each excel at different parts of this workflow.

## Project Overview & Live Statistics

Here are the current project statistics, verified directly from GitHub at publication time:

| Tool | Repository | Stars | Language | Last Updated |
|------|-----------|-------|----------|-------------|
| **OWASP Amass** | OWASP/Amass | 14,453 | Go | April 17, 2026 |
| **Subfinder** | projectdiscovery/subfinder | 13,482 | Go | April 22, 2026 |
| **MassDNS** | blechscharte/massdns | 3,573 | C | April 15, 2026 |

All three projects are actively maintained and widely used in the security community. Amass is backed by the OWASP Foundation, Subfinder is part of ProjectDiscovery's ecosystem (alongside Nuclei and Naabu), and MassDNS is the go-to high-performance DNS resolver for security researchers.

## OWASP Amass: In-Depth Attack Surface Mapping

OWASP Amass is the most comprehensive DNS reconnaissance tool available. It goes beyond simple subdomain enumeration to build a detailed attack surface map through multiple data sources, including:

- **DNS queries** (A, AAAA, CNAME, MX, NS, TXT, SOA, SRV records)
- **Web scraping** of search engines, certificate transparency logs, and security databases
- **API integrations** with Shodan, Censys, VirusTotal, SecurityTrails, and 40+ other sources
- **Network infrastructure discovery** (reverse DNS, ASN mapping, IP range enumeration)
- **Graph database storage** for visualizing relationships between assets

### Docker Deployment

```yaml
# docker-compose-amass.yml
version: '3.8'

services:
  amass:
    image: owasp/amass:latest
    container_name: amass
    volumes:
      - ./amass-config:/root/.config/amass
      - ./amass-output:/root/amass-output
    entrypoint: ["amass"]
    command: ["enum", "-d", "example.com", "-o", "/root/amass-output/results.txt"]
    restart: "no"
```

Create a configuration directory with your API keys for passive sources:

```bash
mkdir -p amass-config amass-output
cat > amass-config/config.ini << 'CONFIGEOF'
# OWASP Amass Configuration
[scope]
  # Define additional domains to include in enumeration
  # domain = example.net

[sources]
  # Enable/disable specific data sources
  minimum_ttl = 1440

  [sources.Censys]
    key = "your-censys-api-key"
    secret = "your-censys-secret"

  [sources.Shodan]
    key = "your-shodan-api-key"

  [sources.VirusTotal]
    key = "your-virustotal-api-key"
CONFIGEOF
```

Run with custom configuration:

```bash
docker compose -f docker-compose-amass.yml up
```

For a full enumeration with config file:

```bash
docker run --rm -v $(pwd)/amass-config:/root/.config/amass \
  -v $(pwd)/amass-output:/root/amass-output \
  owasp/amass:latest enum -d example.com \
  -config /root/.config/amass/config.ini \
  -o /root/amass-output/results.txt
```

### Key Amass Commands

```bash
# Basic subdomain enumeration
amass enum -d example.com

# Passive-only enumeration (no active DNS queries)
amass enum -passive -d example.com

# Enumerate with specific data sources
amass enum -d example.com -src -ip

# Visual graph output
amass viz -dir amass_output -d3

# Track changes over time (compare with previous scan)
amass track -d example.com
```

## ProjectDiscovery Subfinder: Fast Passive Enumeration

Subfinder is designed for speed. It queries dozens of passive data sources in parallel to discover subdomains without sending a single DNS query to the target. This makes it ideal for:

- **Quick reconnaissance** — results in seconds, not minutes
- **CI/CD integration** — fast enough to run on every pull request
- **Monitoring pipelines** — schedule frequent scans to detect new subdomains
- **Stealth assessments** — zero network interaction with the target infrastructure

### Docker Deployment

```yaml
# docker-compose-subfinder.yml
version: '3.8'

services:
  subfinder:
    image: projectdiscovery/subfinder:latest
    container_name: subfinder
    volumes:
      - ./subfinder-config:/root/.config/subfinder
      - ./subfinder-output:/root/output
    entrypoint: ["subfinder"]
    command: ["-d", "example.com", "-o", "/root/output/subdomains.txt", "-nW"]
    restart: "no"
```

Subfinder's provider configuration follows the ProjectDiscovery ecosystem pattern:

```bash
mkdir -p subfinder-config subfinder-output
cat > subfinder-config/provider-config.yaml << 'PROVEOF'
# Subfinder API Configuration
# Add your API keys for sources that support them

censys:
  - token: "your-censys-api-key:your-censys-secret"

shodan:
  - token: "your-shodan-api-key"

virustotal:
  - token: "your-virustotal-api-key"

securitytrails:
  - token: "your-securitytrails-api-key"
PROVEOF
```

Run with provider config:

```bash
docker compose -f docker-compose-subfinder.yml up
```

### Key Subfinder Commands

```bash
# Basic passive enumeration
subfinder -d example.com -o results.txt

# Multiple domains from a file
subfinder -dL domains.txt -o results.txt -nW

# Silent mode (no banner, JSON output)
subfinder -d example.com -json -silent

# Use specific sources only
subfinder -d example.com -sources shodan,censys,virustotal

# Recursive mode (enumerate found subdomains)
subfinder -d example.com -recursive -timeout 30
```

The `-nW` flag (no-wildcard) automatically filters out wildcard DNS responses, which reduces false positives significantly.

## MassDNS: High-Performance Active Brute-Forcing

MassDNS is fundamentally different from Amass and Subfinder. While those tools focus on passive enumeration, MassDNS is a **high-performance DNS stub resolver** designed for active brute-forcing. It can resolve millions of DNS queries per minute, making it the fastest tool for:

- **Subdomain brute-forcing** — test large wordlists against DNS resolvers
- **DNS enumeration at scale** — validate thousands of discovered candidates
- **Zone transfer testing** — attempt AXFR queries across nameservers
- **Record-type enumeration** — discover services via SRV, TXT, MX records

### Docker Deployment

```yaml
# docker-compose-massdns.yml
version: '3.8'

services:
  massdns:
    image: blechschmidt/massdns:latest
    container_name: massdns
    volumes:
      - ./massdns-input:/input
      - ./massdns-output:/output
      - ./resolvers.txt:/resolvers.txt:ro
    entrypoint: ["./bin/massdns"]
    command: [
      "-r", "/resolvers.txt",
      "-t", "A",
      "-w", "/output/results.txt",
      "-o", "S",
      "/input/subdomains.txt"
    ]
    restart: "no"
```

You'll need a list of public DNS resolvers. Create a `resolvers.txt` file:

```bash
# Create input/output directories
mkdir -p massdns-input massdns-output

# Generate or download resolvers list
cat > resolvers.txt << 'RESEOF'
8.8.8.8:53
8.8.4.4:53
1.1.1.1:53
1.0.0.1:53
9.9.9.9:53
208.67.222.222:53
RESEOF
```

Generate a wordlist and run the brute-force:

```bash
# Generate subdomain candidates using a wordlist
while read sub; do echo "${sub}.example.com"; done < subdomains-wordlist.txt > massdns-input/subdomains.txt

# Run MassDNS
docker compose -f docker-compose-massdns.yml up
```

### Key MassDNS Commands

```bash
# Basic DNS resolution from wordlist
massdns -r resolvers.txt -t A -w results.txt subdomains.txt

# Output in simple format (domain + IP)
massdns -r resolvers.txt -t A -o S -w results.txt subdomains.txt

# Bruteforce mode with wordlist
massdns -r resolvers.txt -t A -b -w results.txt -o S subdomains.txt

# Filter valid results only
massdns -r resolvers.txt -t A subdomains.txt | grep -E " NOERROR| A " > valid.txt
```

For maximum performance, use the `-s` flag to set the number of concurrent threads (default is 10000):

```bash
massdns -r resolvers.txt -t A -s 25000 -w results.txt subdomains.txt
```

## Feature Comparison Table

| Feature | OWASP Amass | Subfinder | MassDNS |
|---------|-------------|-----------|---------|
| **Enumeration type** | Active + Passive | Passive only | Active brute-force |
| **Speed** | Moderate | Fast | Very Fast (millions/min) |
| **API integrations** | 40+ sources | 30+ sources | None |
| **DNS brute-forcing** | Yes (built-in) | No | Yes (primary function) |
| **Graph database** | Yes (Neo4j, Bolt) | No | No |
| **ASN/Infrastructure** | Yes | No | No |
| **Certificate transparency** | Yes | Yes | No |
| **JSON output** | Yes | Yes | No (text only) |
| **Docker support** | Official image | Official image | Official image |
| **Wildcard filtering** | Manual | Automatic (-nW) | Manual |
| **Recursive enumeration** | Yes | Yes (-recursive) | No |
| **Language** | Go | Go | C |
| **License** | Apache 2.0 | MIT | MIT |
| **Best use case** | Comprehensive attack surface mapping | Quick passive discovery | High-volume DNS resolution |

## Combining All Three Tools: Production Pipeline

For the most thorough subdomain enumeration, combine all three tools in a single pipeline:

```yaml
# docker-compose-recon.yml
version: '3.8'

services:
  subfinder-passive:
    image: projectdiscovery/subfinder:latest
    container_name: subfinder-passive
    volumes:
      - ./output:/root/output
    entrypoint: ["subfinder"]
    command: ["-d", "example.com", "-o", "/root/output/subfinder.txt", "-nW", "-silent"]
    restart: "no"

  amass-full:
    image: owasp/amass:latest
    container_name: amass-full
    volumes:
      - ./output:/root/amass-output
    entrypoint: ["amass"]
    command: ["enum", "-d", "example.com", "-o", "/root/amass-output/amass.txt"]
    depends_on:
      - subfinder-passive
    restart: "no"

  massdns-brute:
    image: blechschmidt/massdns:latest
    container_name: massdns-brute
    volumes:
      - ./wordlists:/input
      - ./output:/output
      - ./resolvers.txt:/resolvers.txt:ro
    entrypoint: ["./bin/massdns"]
    command: [
      "-r", "/resolvers.txt",
      "-t", "A",
      "-w", "/output/massdns.txt",
      "-o", "S",
      "/input/combined.txt"
    ]
    depends_on:
      - amass-full
    restart: "no"
```

Run the pipeline and merge results:

```bash
docker compose -f docker-compose-recon.yml up

# Merge, deduplicate, and sort all results
cat output/subfinder.txt output/amass.txt > output/combined.txt
sort -u output/combined.txt > output/all-subdomains.txt
wc -l output/all-subdomains.txt

# Use combined list for MassDNS brute-force
docker compose -f docker-compose-recon.yml up massdns-brute
```

### Automated Scheduling with Cron

```bash
# Add to crontab for daily reconnaissance
0 2 * * * cd /opt/dns-recon && docker compose -f docker-compose-recon.yml up --quiet-pull && \
  cat output/subfinder.txt output/amass.txt | sort -u > output/latest.txt && \
  diff output/latest.txt output/previous.txt | mail -s "DNS Recon Changes" admin@example.com && \
  cp output/latest.txt output/previous.txt
```

## Choosing the Right Tool

**Use OWASP Amass when:**
- You need the most comprehensive attack surface analysis possible
- Infrastructure mapping (ASN, IP ranges, reverse DNS) is important
- You want visual graph output for reporting
- Time is less important than completeness

**Use Subfinder when:**
- You need fast results for time-sensitive assessments
- Stealth is required (no active DNS queries to the target)
- You're integrating into CI/CD pipelines or automated workflows
- You're already using other ProjectDiscovery tools (Nuclei, Naabu)

**Use MassDNS when:**
- You need to validate thousands of subdomain candidates quickly
- Brute-forcing with large wordlists is your primary strategy
- You need maximum DNS resolution throughput
- You're working with limited bandwidth and need efficient resolver usage

**Best practice:** Run Subfinder first for quick passive results, then Amass for deep enumeration, and finally MassDNS to validate and brute-force the combined candidate list. This gives you the speed of passive discovery, the depth of active enumeration, and the thoroughness of brute-force validation.

For monitoring your DNS infrastructure changes, also consider our [DNS monitoring tools guide](../best-self-hosted-dns-monitoring-tools-dnstop-packetbeat-arkime-guide-2026/) and [DNS firewall with RPZ guide](../self-hosted-dns-firewall-rpz-unbound-powerdns-bind9-knot-guide-2026/).

## FAQ

### What is the difference between passive and active DNS reconnaissance?

Passive DNS reconnaissance queries public data sources (search engines, certificate transparency logs, DNS databases) without directly communicating with the target's DNS servers. Active reconnaissance sends actual DNS queries to the target's nameservers. Passive methods are stealthier but may miss recently created or unindexed subdomains. Active methods are more thorough but generate network traffic that can be detected.

### Is it legal to perform DNS reconnaissance on domains I don't own?

DNS reconnaissance using publicly available information (passive enumeration) is generally legal, as you are querying public DNS records and public databases. However, active brute-forcing may violate the target's terms of service and could be considered unauthorized access in some jurisdictions. Always obtain explicit permission before running DNS enumeration against any domain you do not own.

### How many subdomains can these tools typically find?

The number varies dramatically by domain. A small company might have 10-50 subdomains, while large enterprises can have 500-5,000+. Subfinder typically returns results in 10-30 seconds, Amass takes 2-10 minutes for a comprehensive scan, and MassDNS can validate 100,000+ candidates per minute depending on your resolver list and network conditions.

### Can I run all three tools on a low-resource server?

Yes. All three tools are lightweight. Subfinder and Amass (written in Go) typically use 50-200MB RAM during enumeration. MassDNS (written in C) is even more efficient, using under 50MB even at maximum thread counts. A VPS with 1GB RAM and 1 vCPU is sufficient for running any of them individually. Running all three simultaneously may require 2GB RAM for optimal performance.

### How do I reduce false positives from wildcard DNS records?

Wildcard DNS can make it appear that every subdomain exists when it actually resolves to a catch-all address. Subfinder handles this automatically with the `-nW` flag. For Amass, review results and filter manually. For MassDNS, compare resolved IPs against known wildcard IPs: run a query for a random non-existent subdomain, note the IP, then filter your results to exclude that IP address.

### What wordlist should I use with MassDNS for subdomain brute-forcing?

The most popular wordlists are `all.txt` from the SecLists project (containing 1+ million subdomain entries) and Daniel Miessler's SecLists DNS subdomains list. For most targets, the top 10,000-50,000 most common subdomain prefixes will discover 80-90% of results. Start with a smaller wordlist and expand if needed.

### How often should I run DNS reconnaissance scans?

For production monitoring, run passive scans (Subfinder) daily and full Amass scans weekly. If you manage a large attack surface, consider running Subfinder every 6 hours. MassDNS brute-forcing should run less frequently (weekly or monthly) since most subdomains don't change that rapidly. Set up diff-based alerting to notify you only when new subdomains appear.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Amass vs Subfinder vs MassDNS: Self-Hosted DNS Reconnaissance & Subdomain Enumeration Guide 2026",
  "description": "Compare OWASP Amass, ProjectDiscovery Subfinder, and MassDNS for self-hosted DNS reconnaissance and subdomain enumeration. Complete Docker deployment guide with configs, comparison tables, and best practices.",
  "datePublished": "2026-04-23",
  "dateModified": "2026-04-23",
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
