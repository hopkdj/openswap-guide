---
title: "DNSdiag vs DNSRecon vs DNSenum: Self-Hosted DNS Testing Tools 2026"
date: 2026-04-27
tags: ["comparison", "guide", "self-hosted", "dns", "security", "networking"]
draft: false
description: "Compare DNSdiag, DNSRecon, and DNSenum for self-hosted DNS testing, diagnostics, and troubleshooting. Includes Docker setup, usage examples, and feature comparison."
---

When managing self-hosted DNS infrastructure, knowing how to test, diagnose, and troubleshoot your nameservers is essential. Commercial DNS testing suites cost thousands of dollars, but three open-source tools — **DNSdiag**, **DNSRecon**, and **DNSenum** — provide powerful DNS diagnostics, enumeration, and security auditing capabilities you can run from your own server.

This guide compares these three tools, walks through Docker deployment, and shows you how to use each one for real-world DNS troubleshooting scenarios.

## Why Self-Hosted DNS Testing Matters

DNS is the backbone of every self-hosted service. If your resolver is slow, misconfigured, or vulnerable to cache poisoning, every application on your network suffers. Commercial DNS testing platforms like Infoblox Trinzic or Cisco Network Registrar include built-in diagnostics, but they come with enterprise price tags.

Running your own DNS testing toolkit gives you:

- **No data leakage** — All queries stay within your network or target only your own domains
- **Cost-free operation** — Open-source tools with no licensing fees
- **Automation-ready** — Scriptable via CLI for CI/CD pipelines and cron jobs
- **Offline capability** — Works without external API access or cloud dependencies
- **Customizable** — Extend with plugins, custom wordlists, and integration with monitoring stacks

Whether you are testing resolver latency after switching from a cloud DNS provider to a self-hosted Unbound instance, or verifying that your zone transfers are properly restricted, having the right toolkit is critical.

## Tool Overview

### DNSdiag (farrokhi/dnsdiag)

**GitHub:** [farrokhi/dnsdiag](https://github.com/farrokhi/dnsdiag) · **Stars:** 1,040 · **Language:** Python

DNSdiag is a comprehensive DNS measurement, troubleshooting, and security auditing toolset. Unlike single-purpose tools, it bundles four sub-tools into one package:

- **dnsping** — ICMP-ping-equivalent for DNS servers. Measures latency, packet loss, jitter, and response time distribution
- **dnstraceroute** — Traceroute for DNS resolution paths. Discovers each recursive resolver hop between you and the target
- **dnsfuzz** — DNS fuzzing tool that generates unexpected record queries to find misconfigurations or hidden records
- **dnseval** — Compares multiple DNS servers side-by-side, measuring response time, flags, and answer consistency

The tool is actively maintained, supports Python 3.10+, and runs on Linux, macOS, and in Docker containers.

### DNSRecon (darkoperator/dnsrecon)

**GitHub:** [darkoperator/dnsrecon](https://github.com/darkoperator/dnsrecon) · **Stars:** 3,008 · **Language:** Python

DNSRecon is one of the most feature-rich DNS enumeration scripts available. It performs comprehensive DNS reconnaissance including:

- Zone transfer attempts (AXFR/IXFR)
- Standard record enumeration (A, AAAA, MX, NS, SOA, TXT, SRV, PTR)
- Reverse lookups on IP ranges
- Top-level domain (TLD) expansion
- Subdomain brute-force with custom wordlists
- Google and Bing scraping for subdomain discovery
- SRV record enumeration
- DNSSEC validation checks
- Wildcard resolution detection

DNSRecon outputs results in multiple formats (CSV, XML, JSON, SQLite) and integrates well with other security tooling.

### DNSenum (waKKu/dnsenum)

**GitHub:** [waKKu/dnsenum](https://github.com/waKKu/dnsenum) · **Stars:** 1,200 · **Language:** Perl

DNSenum is a Perl-based DNS enumeration and security testing tool focused on discovering subdomains, mail servers, and zone transfer vulnerabilities. Its key features include:

- Zone transfer testing with all authoritative nameservers
- Subdomain brute-force using internal and external wordlists
- Google scraping for subdomain discovery
- Reverse Class C lookup for IP range enumeration
- WHOIS netrange and nameserver discovery
- NS, A, MX, and SOA record enumeration
- Zone transfer validation and reporting
- Output to text files and Bind zone file format

DNSenum is lightweight, requires minimal dependencies, and is particularly effective for quick reconnaissance scans.

## Feature Comparison

| Feature | DNSdiag | DNSRecon | DNSenum |
|---|---|---|---|
| **Primary Purpose** | DNS diagnostics & performance | DNS enumeration & recon | DNS enumeration & zone testing |
| **DNS Ping** | ✅ dnsping (latency, jitter, loss) | ❌ | ❌ |
| **DNS Traceroute** | ✅ dnstraceroute (resolver path) | ❌ | ❌ |
| **DNS Fuzzing** | ✅ dnsfuzz (unexpected records) | ❌ | ❌ |
| **Server Comparison** | ✅ dnseval (multi-server benchmark) | ❌ | ❌ |
| **Zone Transfer (AXFR)** | ❌ | ✅ | ✅ |
| **Subdomain Brute-Force** | ❌ | ✅ (custom wordlists) | ✅ (built-in + custom) |
| **Google/Bing Scraping** | ❌ | ✅ | ✅ |
| **Record Enumeration** | Basic | ✅ Comprehensive (15+ types) | ✅ Standard types |
| **Reverse Lookup** | ❌ | ✅ IP range reverse | ✅ Class C reverse |
| **DNSSEC Validation** | ❌ | ✅ | ❌ |
| **Wildcard Detection** | ❌ | ✅ | ✅ |
| **WHOIS Integration** | ❌ | ❌ | ✅ |
| **Docker Support** | ✅ Dockerfile | ✅ Dockerfile | No Dockerfile |
| **Output Formats** | Terminal/CSV | CSV, XML, JSON, SQLite | Text, Bind zone file |
| **Language** | Python | Python | Perl |
| **License** | BSD-3-Clause | GPL-3.0 | GPL-2.0 |

## Docker Installation and Setup

### DNSdiag

DNSdiag includes a Dockerfile in the repository root. Build and run it directly:

```bash
git clone https://github.com/farrokhi/dnsdiag.git
cd dnsdiag
docker build -t dnsdiag .
```

Run dnsping against Google DNS:

```bash
docker run --rm dnsdiag dnsping.py -c 10 -s 8.8.8.8 google.com
```

Run dnseval to compare multiple resolvers:

```bash
docker run --rm dnsdiag dnseval.py -f public-v4.txt google.com
```

Run dnstraceroute to map the resolver path:

```bash
docker run --rm dnsdiag dnstraceroute.py 8.8.8.8 google.com
```

### DNSRecon

DNSRecon also ships with a Dockerfile:

```bash
git clone https://github.com/darkoperator/dnsrecon.git
cd dnsrecon
docker build -t dnsrecon .
```

Perform a standard enumeration scan:

```bash
docker run --rm dnsrecon -d example.com -t std
```

Run a zone transfer attempt:

```bash
docker run --rm dnsrecon -d example.com -t axfr
```

Brute-force subdomains with a custom wordlist:

```bash
docker run --rm -v $(pwd)/wordlist.txt:/app/wordlist.txt dnsrecon \
  -d example.com -t brt -D /app/wordlist.txt
```

### DNSenum

DNSenum does not include an official Dockerfile, but you can easily containerize it:

```bash
git clone https://github.com/waKKu/dnsenum.git
cd dnsenum
```

Create a simple Dockerfile:

```dockerfile
FROM alpine:latest
RUN apk add --no-cache perl perl-net-dns perl-net-ip perl-net-whois-ip \
    perl-io-socket-inet6 perl-term-readkey unzip
WORKDIR /app
COPY . /app
RUN chmod +x dnsenum.pl
ENTRYPOINT ["perl", "/app/dnsenum.pl"]
```

Build and run:

```bash
docker build -t dnsenum .
docker run --rm dnsenum --threads 20 --noreverse example.com
```

## Usage Scenarios

### Scenario 1: Testing DNS Resolver Performance After Migration

You just migrated from Google DNS (8.8.8.8) to a self-hosted Unbound resolver. Use DNSdiag's dnseval to compare:

```bash
dnseval.py -f <(echo -e "8.8.8.8\n1.1.1.1\n192.168.1.10") example.com
```

Sample output:

```
server              avg_resp    min_resp    max_resp    std_dev     lost(%)
--------------------------------------------------------------
8.8.8.8             12.3ms      8.1ms       45.2ms      7.4ms       0%
1.1.1.1             9.8ms       6.2ms       32.1ms      5.1ms       0%
192.168.1.10        1.2ms       0.8ms       3.4ms       0.5ms       0%
```

Your local resolver shows 1.2ms average — a 10x improvement over cloud resolvers for internal queries.

### Scenario 2: Verifying Zone Transfer Restrictions

After configuring your BIND9 authoritative server, verify that zone transfers are properly restricted to your secondary nameservers only:

```bash
dnsrecon -d yourdomain.com -t axfr
dnsenum --dnsserver ns1.yourdomain.com yourdomain.com
```

If zone transfers are properly restricted, both tools should report failure. If they succeed and dump your full zone file, you have a security issue that needs immediate remediation.

### Scenario 3: Discovering the DNS Resolution Path

When troubleshooting slow DNS resolution, use dnstraceroute to see which recursive resolvers your queries traverse:

```bash
dnstraceroute.py 8.8.8.8 yourdomain.com
```

This reveals each hop in the resolution chain, helping you identify slow or misconfigured intermediate resolvers that add latency to your queries.

### Scenario 4: Subdomain Discovery for Security Audits

Before deploying a new self-hosted service, enumerate existing subdomains to avoid conflicts and identify forgotten services:

```bash
dnsrecon -d yourdomain.com -t std,brt -D /usr/share/wordlists/dnsmap.txt
dnsenum --threads 30 --noreverse yourdomain.com
```

Both tools will discover subdomains through brute-force, zone transfers, and search engine scraping. Cross-reference the results for comprehensive coverage.

## Choosing the Right Tool

| Your Goal | Best Tool | Why |
|---|---|---|
| Measure DNS latency and jitter | **DNSdiag** (dnsping) | Purpose-built for DNS ping testing with statistical output |
| Compare multiple DNS servers | **DNSdiag** (dnseval) | Tests multiple resolvers side-by-side in a single command |
| Discover resolver path | **DNSdiag** (dnstraceroute) | Only tool with DNS-aware traceroute capability |
| Comprehensive DNS enumeration | **DNSRecon** | Broadest range of record types and discovery methods |
| Quick zone transfer check | **DNSenum** | Fastest for a single zone transfer test |
| Subdomain brute-force | **DNSRecon** or **DNSenum** | Both support custom wordlists; DNSRecon has more output formats |
| DNS security fuzzing | **DNSdiag** (dnsfuzz) | Only tool with DNS fuzzing capability |
| Full reconnaissance report | **DNSRecon** | JSON/XML/SQLite output integrates with reporting pipelines |

For a complete DNS infrastructure, consider combining these tools: use **DNSdiag** for ongoing performance monitoring of your resolvers, **DNSRecon** for periodic security audits, and **DNSenum** for quick zone transfer and subdomain checks.

If you are also managing authoritative DNS servers, check out our [PowerDNS vs BIND9 vs NSD guide](../2026-04-18-powerdns-vs-bind9-vs-nsd-vs-knot-self-hosted-authoritative-dns-2026/) for choosing the right nameserver, and our [DNSSEC management comparison](../opendnssec-vs-knot-dns-vs-bind-self-hosted-dnssec-management-guide-2026/) for securing your zones. For DNS traffic analysis after testing, see our [pktvisor vs DNS Collector guide](../2026-04-26-pktvisor-vs-dns-collector-vs-dsc-self-hosted-dns-traffic-analysis-guide-2026/).

## FAQ

### What is the difference between DNSdiag and DNSRecon?

DNSdiag focuses on DNS diagnostics and performance testing — measuring latency (dnsping), tracing resolution paths (dnstraceroute), comparing servers (dnseval), and fuzzing (dnsfuzz). DNSRecon is primarily a DNS enumeration and reconnaissance tool that discovers records, attempts zone transfers, brute-forces subdomains, and validates DNSSEC. Use DNSdiag for testing and benchmarking; use DNSRecon for discovery and security auditing.

### Can I run DNSdiag in a Docker container?

Yes. DNSdiag includes an official Dockerfile in the repository root. Build it with `docker build -t dnsdiag .` and run any sub-tool via `docker run --rm dnsdiag dnsping.py -c 10 -s 8.8.8.8 example.com`. The container includes all Python dependencies and runs on Alpine Linux for a minimal footprint.

### Does DNSenum support Docker?

DNSenum does not ship with an official Dockerfile, but you can easily create one using Alpine Linux with Perl and the required Perl modules (Net::DNS, Net::IP, Net::Whois::IP). The Dockerfile provided in this guide works out of the box. Alternatively, install DNSenum directly on your host with `apt install dnsenum` on Debian-based systems.

### Which tool is best for testing DNS resolver latency?

DNSdiag's **dnsping** is purpose-built for this. It sends DNS queries repeatedly to a target resolver and reports average latency, minimum/maximum response time, standard deviation, and packet loss percentage — the same statistics you would expect from ICMP ping but for DNS queries. Run `dnsping.py -c 100 -s 8.8.8.8 example.com` for a 100-query benchmark.

### How do I test if my DNS zone transfer is properly restricted?

Use either DNSRecon (`dnsrecon -d yourdomain.com -t axfr`) or DNSenum (`dnsenum yourdomain.com`). Both will attempt a zone transfer against all authoritative nameservers for the domain. If the transfer succeeds and dumps your full zone file, your nameserver configuration needs to be tightened to restrict AXFR to trusted secondary servers only.

### Can these tools be automated for continuous monitoring?

Yes. All three tools are CLI-based and scriptable. DNSdiag's dnsping and dnseval are particularly well-suited for cron-based monitoring — you can run them on a schedule, capture output to files, and feed the data into Grafana, Prometheus, or your preferred alerting system. DNSRecon's JSON and SQLite output formats make it easy to parse results programmatically.

### Is DNSRecon better than DNSenum for subdomain discovery?

Both tools are effective for subdomain discovery through brute-force and search engine scraping. DNSRecon offers more output formats (CSV, XML, JSON, SQLite) and includes DNSSEC validation and wildcard detection. DNSenum is faster for quick scans and includes WHOIS integration. For thorough subdomain enumeration, running both tools and cross-referencing results gives the most comprehensive coverage.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "DNSdiag vs DNSRecon vs DNSenum: Self-Hosted DNS Testing Tools 2026",
  "description": "Compare DNSdiag, DNSRecon, and DNSenum for self-hosted DNS testing, diagnostics, and troubleshooting. Includes Docker setup, usage examples, and feature comparison.",
  "datePublished": "2026-04-27",
  "dateModified": "2026-04-27",
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
