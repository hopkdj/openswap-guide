---
title: "Self-Hosted Network Port Scanners: Masscan vs RustScan vs Naabu"
date: "2026-05-14"
tags: ["network-security", "port-scanning", "network-reconnaissance", "self-hosted"]
draft: false
---

Network port scanning is a foundational technique in network security, used by administrators to audit firewall rules, discover running services, and identify potential attack surfaces. While cloud-based scanners exist, self-hosted port scanners give you full control over scan parameters, data retention, and scheduling — without sharing your network topology with third parties.

In this guide, we compare three modern open-source port scanning tools you can deploy on your own infrastructure: **Masscan**, **RustScan**, and **Naabu**. Each takes a different approach to the problem, from raw packet-speed scanning to developer-friendly workflows.

## Understanding Network Port Scanning

Port scanning involves sending probe packets to target IP addresses and analyzing responses to determine which TCP or UDP ports are open, closed, or filtered. The technique has been essential to network administration since the early days of TCP/IP.

There are several scanning techniques:

- **TCP SYN scan** — sends SYN packets and analyzes responses (half-open scan, stealthy)
- **TCP Connect scan** — completes the full TCP three-way handshake (reliable but noisy)
- **UDP scan** — sends UDP datagrams and checks for ICMP port unreachable responses
- **ACK scan** — used to map firewall rulesets and determine stateful filtering
- **XMAS/NULL/FIN scan** — sends packets with specific flag combinations to bypass simple firewalls

Modern port scanners also support banner grabbing, service version detection, and output formatting for integration with vulnerability management pipelines.

## Why Self-Host Port Scanners?

Running port scanners on your own infrastructure offers several advantages over cloud-based alternatives:

**Network proximity** — Scanning from within your network gives you an attacker's-eye view of what's actually reachable. External scanners can't detect internal-only services or lateral movement paths.

**No rate limits** — Cloud scanners throttle your scans to avoid being blocked. Self-hosted tools let you control scan speed based on your network's capacity and your operational needs.

**Data privacy** — Scan results contain sensitive information about your network topology. Keeping this data on-premises eliminates the risk of exposure through third-party breaches.

**Continuous monitoring** — Self-hosted scanners can run on a schedule, integrating with your SIEM or alerting pipeline to detect unauthorized service deployments.

**Cost efficiency** — At scale, self-hosted scanning is significantly cheaper than per-scan cloud pricing.

## Comparison Table

| Feature | Masscan | RustScan | Naabu |
|---------|---------|----------|-------|
| **Language** | C | Rust | Go |
| **GitHub Stars** | 13,900+ | 19,400+ | 3,500+ |
| **Scan Speed** | 10M pps | 100K+ ports/sec | 1.5M pps |
| **TCP SYN Scan** | Yes | Yes | Yes |
| **UDP Scan** | Yes | Yes | Yes |
| **Banner Grabbing** | Yes | Yes (via Nmap) | Yes (built-in) |
| **CDN/Ranges** | Yes | No | Yes |
| **Output Formats** | XML, JSON, grepable | JSON, CSV, Nmap XML | JSON, CSV, TXT |
| **Nmap Integration** | Pipe results | Built-in runner | Pipe results |
| **IPv6 Support** | Yes | Yes | Yes |
| **Port Range** | 0-65535 | 0-65535 | 0-65535 |
| **Docker Image** | Official | Community | Official |
| **License** | AGPL-3.0 | GPL-2.0 | MIT |

## Masscan: The Fastest Internet-Scale Scanner

[Masscan](https://github.com/robertdavidgraham/masscan) by Robert Graham is the fastest port scanner available, capable of scanning the entire Internet in under 6 minutes at 10 million packets per second. It uses an asynchronous transmission model similar to scanrand, unicornscan, and ZMap, but with a custom TCP stack that avoids OS-level limitations.

### Installation

```bash
# From source
git clone https://github.com/robertdavidgraham/masscan.git
cd masscan
make
sudo make install

# Ubuntu/Debian
sudo apt-get install masscan

# Docker
docker run --rm --network host robertdavidgraham/masscan --help
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  masscan:
    image: robertdavidgraham/masscan:latest
    network_mode: host
    volumes:
      - ./output:/output
    command: >
      10.0.0.0/8 -p 1-65535 --rate 100000
      --output-format json
      --output-filename /output/results.json
    restart: "no"
```

### Key Features

- **Raw packet transmission** — Bypasses OS TCP stack for maximum speed
- **Flexible target specification** — Supports IP ranges, CIDR notation, and exclusion lists
- **HTTP banner grabbing** — Can grab HTTP banners to identify web services
- **Randomized scanning** — Shuffles target order to avoid detection patterns

### Example Usage

```bash
# Scan a subnet for common ports
masscan 192.168.1.0/24 -p80,443,8080 --rate 10000 -oJ results.json

# Full port scan with banner grabbing
masscan 10.0.0.0/8 -p0-65535 --banners --rate 500000 -oX full_scan.xml

# Scan with exclusion file (don't scan your own IPs)
masscan 0.0.0.0/0 -p80 --excludefile exclude.txt --rate 100000
```

## RustScan: The Modern Developer-Friendly Scanner

[RustScan](https://github.com/RustScan/RustScan) is a modern port scanner written in Rust that prioritizes developer experience. It uses asynchronous I/O for fast scanning and seamlessly pipes results into Nmap for detailed service enumeration — giving you the best of both worlds: speed and depth.

### Installation

```bash
# Cargo (Rust package manager)
cargo install rustscan

# From pre-built binary
curl -sL https://raw.githubusercontent.com/RustScan/RustScan/master/scripts/install.sh | bash

# Docker
docker run -it --rm --net host rustscan/rustscan --help
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  rustscan:
    image: rustscan/rustscan:latest
    network_mode: host
    volumes:
      - ./output:/output
      - ~/.rustscan:/root/.rustscan:ro
    command: >
      -a 192.168.1.0/24
      -p 1-1000
      --batch-size 4500
      --timeout 1500
      -o /output/results.txt
    restart: "no"
```

### Key Features

- **Adaptive timeout** — Automatically adjusts timeout based on network conditions
- **Nmap integration** — Pipes open ports directly to Nmap scripts for enumeration
- **Bulk scanning** — Scans multiple hosts in parallel with configurable batch sizes
- **Configuration files** — Supports `.rustscan.toml` for default settings
- **Script support** — Can run custom scripts against discovered ports

### Example Usage

```bash
# Quick scan with Nmap follow-up
rustscan -a 192.168.1.100 -- -A -sC -sV

# Scan multiple hosts with custom port range
rustscan -a 10.0.0.0/24 -p 1-65535 --batch-size 5000

# Scan with Nmap scripts for vulnerability detection
rustscan -a 192.168.1.50 -- -sV --script vuln
```

## Naabu: The ProjectDiscovery Scanner

[Naabu](https://github.com/projectdiscovery/naabu) is a fast port scanner from ProjectDiscovery, designed to be reliable and easy to integrate into security workflows. It features a clean CLI, built-in service detection, and seamless integration with other ProjectDiscovery tools like Nuclei and Subfinder.

### Installation

```bash
# Go install
go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest

# From pre-built binary
curl -sL https://github.com/projectdiscovery/naabu/releases/latest/download/naabu_linux_amd64.zip | unzip -d /usr/local/bin

# Docker
docker run -it --rm projectdiscovery/naabu -help
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  naabu:
    image: projectdiscovery/naabu:latest
    network_mode: host
    volumes:
      - ./output:/output
      - ./wordlist:/wordlist
    command: >
      -target 192.168.1.0/24
      -port 1-65535
      -rate 100000
      -json
      -o /output/scan_results.json
    restart: "no"
```

### Key Features

- **SYN/Connect scan modes** — Choose between raw SYN scans or TCP connect scans
- **Built-in service detection** — Identifies common services on open ports
- **CDN exclusion** — Automatically excludes known CDN IPs to reduce false positives
- **Host discovery** — Includes ping and ARP-based host discovery
- **ProjectDiscovery ecosystem** — Integrates with Nuclei, Subfinder, and httpx

### Example Usage

```bash
# Scan targets from a file
naabu -l targets.txt -p top-1000 -json -o results.json

# Full port scan with service detection
naabu -host 10.0.0.0/24 -p - -rate 100000 -nmap-cli "nmap -sV"

# Scan specific ports with CDN exclusion
naabu -host example.com -exclude-cdn -p 80,443,8080,8443 -json
```

## Choosing the Right Port Scanner

| Use Case | Recommended Tool | Reason |
|----------|-----------------|--------|
| Internet-scale surveys | Masscan | Unmatched speed at 10M pps |
| Internal network audits | RustScan | Developer-friendly with Nmap integration |
| Security assessment pipelines | Naabu | Clean output, ecosystem integration |
| Quick host discovery | RustScan | Adaptive timeouts, easy syntax |
| Penetration testing | Naabu | Service detection, CDN exclusion |
| Continuous monitoring | Masscan | Cron-friendly, high throughput |

## Security Considerations

Port scanning, even on your own network, requires careful consideration:

1. **Obtain proper authorization** — Never scan networks you don't own or have explicit permission to test
2. **Rate limiting** — High-speed scans can trigger IDS/IPS alerts and cause network congestion
3. **Firewall rules** — Ensure your scanner's source IP is permitted through internal firewalls
4. **Scan scheduling** — Run scans during maintenance windows to avoid impacting production services
5. **Data handling** — Store scan results securely; they contain sensitive network topology information
6. **Legal compliance** — Some jurisdictions regulate port scanning activity even on owned networks

## Why Self-Host Your Port Scanners?

Running port scanners on your own infrastructure provides several compelling advantages that cloud-based alternatives simply cannot match. When you control the scanning infrastructure, you eliminate the latency introduced by remote scanning platforms. Scanning from within your network perimeter means you see exactly what an internal attacker would see — open ports on internal-only services, misconfigured firewalls, and shadow IT deployments that external scans would never discover.

Data sovereignty is another critical factor. Port scan results contain detailed maps of your network topology, service inventory, and potential vulnerability surfaces. Transmitting this data to a third-party cloud provider creates an additional attack vector. By keeping scan results on-premises, you maintain full control over who can access this sensitive reconnaissance data.

Cost efficiency becomes significant at scale. Cloud scanning platforms typically charge per scan or per target. For organizations running daily or weekly scans across hundreds of subnets, self-hosted scanners cost only the compute resources they consume — often a fraction of cloud pricing.

Integration with existing security tooling is seamless when the scanner runs on your infrastructure. You can pipe results directly into your SIEM, feed discovered hosts into your CMDB, trigger automated vulnerability scans, or feed open ports into alerting systems. Cloud-based scanners require API integrations that add complexity and potential failure points.

Finally, customization and extensibility matter. Self-hosted scanners can be tuned to your specific network architecture — custom port lists, scan timing optimized for your bandwidth, integration with internal authentication systems, and custom output formats tailored to your reporting requirements.

For network security monitoring, see our [WAF and bot protection guide](../self-hosted-waf-bot-protection-modsecurity-coraza-crowdsec-2026/). For intrusion prevention, check our [fail2ban vs SSHguard comparison](../2026-04-24-fail2ban-vs-sshguard-vs-crowdsec-self-hosted-intrusion-prevention-2026/). For container security scanning, our [Trivy vs Grype vs Clair guide](../2026-04-24-self-hosted-container-image-scanning-trivy-grype-clair-anchore-guide/) covers image-level vulnerability detection.

## FAQ

### What is the fastest self-hosted port scanner?

Masscan is the fastest, capable of scanning at 10 million packets per second. It can scan the entire IPv4 address space in under 6 minutes. However, this speed requires a dedicated network interface and proper kernel tuning to avoid packet drops.

### Can I run port scanners in Docker containers?

Yes, all three tools support Docker. However, for SYN (raw packet) scanning, you need `--network host` or `--cap-add=NET_RAW` to give the container permission to craft raw packets. Without this, scanners fall back to slower TCP connect scans.

### What is the difference between SYN scan and Connect scan?

SYN scan sends only the initial SYN packet and analyzes the response — it never completes the TCP handshake, making it faster and less likely to be logged. Connect scan completes the full three-way handshake, which is slower but more reliable through firewalls and proxy servers.

### Are port scans legal on my own network?

In most jurisdictions, scanning your own network is legal. However, scanning networks you don't own without explicit permission may violate computer fraud laws. Always obtain written authorization before scanning any network you don't fully control.

### How do I avoid triggering IDS/IPS with port scans?

Use slower scan rates, spread scans across time windows, randomize target order (Masscan does this by default), and use Connect scans instead of SYN scans when stealth is more important than speed. RustScan's adaptive timeout helps minimize noisy retransmissions.

### Which scanner should I use for continuous monitoring?

For continuous automated monitoring, Naabu is a strong choice due to its clean JSON output and integration-friendly design. Masscan works well for high-frequency full-network surveys. RustScan is best for on-demand audits where you need Nmap-level detail on discovered ports.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network Port Scanners: Masscan vs RustScan vs Naabu",
  "description": "Compare three open-source self-hosted port scanning tools for network security auditing, vulnerability assessment, and continuous monitoring.",
  "datePublished": "2026-05-14",
  "dateModified": "2026-05-14",
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
