---
title: "Self-Hosted SMTP TLS Reporting — DMARC Report Viewer vs Viesti-Reports vs Rpter"
date: "2026-05-14"
tags: ["email-security", "tls", "monitoring", "smtp", "dmarc"]
draft: false
---

SMTP TLS Reporting (TLS-RPT, RFC 8460) and DMARC aggregate reporting are critical components of email security infrastructure. When you configure MTA-STS (Mail Transfer Agent Strict Transport Security) or DMARC for your domain, receiving mail servers send you daily reports about TLS connection outcomes and authentication results. Managing and interpreting these reports requires dedicated tooling — especially when you receive hundreds of reports per day from major providers like Google, Microsoft, and Yahoo.

In this guide, we compare three open-source, self-hosted solutions for processing and visualizing SMTP TLS and DMARC reports: **DMARC Report Viewer**, **Viesti-Reports**, and **rpter**.

## Why Self-Host TLS and DMARC Report Processing?

Commercial services like Dmarcian, EasyDMARC, and Postmark DMARC offer polished dashboards for report analysis — but they come with monthly fees, data residency concerns, and vendor lock-in. Self-hosting your report processing pipeline gives you full control over your email security data, allows you to correlate TLS reports with your own infrastructure logs, and eliminates ongoing subscription costs.

For organizations managing multiple domains or high email volumes, self-hosted report processing is often the most cost-effective and privacy-preserving approach.

## Understanding SMTP TLS Reporting (RFC 8460)

SMTP TLS Reporting is a mechanism defined in RFC 8460 that allows mail servers to report on the success or failure of STARTTLS connections. When a domain publishes a `_smtp._tls` DNS TXT record with a `rua` (Reporting URI) field, sending MTA servers deliver JSON-formatted reports to that address describing:

- **Total successful TLS connections** — count of connections that completed with valid TLS
- **Policy failures** — connections that failed to meet the domain's TLS policy (MTA-STS)
- **Certificate issues** — expired, self-signed, or mismatched certificates encountered
- **Server reachability** — whether the MX host was reachable at all

These reports complement DMARC aggregate reports, which focus on SPF and DKIM authentication results. Together, they provide a comprehensive picture of your email delivery security posture.

## Tool Comparison

| Feature | DMARC Report Viewer | Viesti-Reports | rpter |
|---------|---------------------|----------------|-------|
| GitHub Stars | 295+ | 115+ | 7+ |
| Language | Python | Python | Rust |
| DMARC Reports | Yes | Yes | Limited |
| TLS-RPT Reports | Yes | Yes | Yes |
| BIMI Support | No | Yes | No |
| IMAP Integration | Yes | Yes | No |
| Web Dashboard | Yes | Yes | CLI |
| Docker Support | Yes | Yes | Yes |
| Active Development | Active | Moderate | Experimental |
| License | MIT | MIT | MIT |

## 1. DMARC Report Viewer (cry-inc/dmarc-report-viewer)

**DMARC Report Viewer** is a lightweight, standalone web application that connects to an IMAP mailbox to fetch and display both DMARC aggregate reports and SMTP TLS reports. It's designed for simplicity — point it at a dedicated mailbox, and it parses incoming reports into a clean, filterable dashboard.

### Key Features

- **IMAP polling** — automatically fetches reports from a configured mailbox
- **Dual report support** — handles both DMARC XML aggregates and TLS-RPT JSON reports
- **Interactive dashboard** — filter by domain, date range, and report type
- **Sender statistics** — visualize which mail providers are sending reports
- **Docker deployment** — official Docker image available

### Docker Compose Configuration

```yaml
version: '3.8'
services:
  dmarc-report-viewer:
    image: ghcr.io/cry-inc/dmarc-report-viewer:latest
    container_name: dmarc-report-viewer
    ports:
      - "8080:8080"
    environment:
      - IMAP_HOST=imap.example.com
      - IMAP_PORT=993
      - IMAP_USER=tls-reports@example.com
      - IMAP_PASSWORD=your-imap-password
      - IMAP_USE_TLS=true
      - IMAP_FOLDER=INBOX
    restart: unless-stopped
    volumes:
      - report-data:/app/data

volumes:
  report-data:
```

### Installation Steps

```bash
# 1. Create a dedicated mailbox for receiving reports
# 2. Update DNS records for each domain:
#    _smtp._tls.example.com. IN TXT "v=TLSRPTv1; rua=mailto:tls-reports@example.com"
# 3. Deploy with Docker Compose:
docker compose up -d
# 4. Access the dashboard at http://localhost:8080
```

### When to Use

DMARC Report Viewer is ideal for small to medium organizations that need a simple, no-fuss solution for viewing incoming TLS and DMARC reports. Its IMAP-based approach means you don't need to set up a dedicated mail server — just point it at any existing IMAP account.

## 2. Viesti-Reports (antedebaas/Viesti-Reports)

**Viesti-Reports** (Finnish: "viesti" = message) is a more feature-rich report processing platform that handles DMARC aggregate reports, SMTP TLS reports, and BIMI (Brand Indicators for Message Identification) indicator hosting. It provides a comprehensive email security dashboard in a single self-hosted application.

### Key Features

- **Triple report support** — DMARC, TLS-RPT, and BIMI in one platform
- **BIMI indicator hosting** — serve your brand logo for BIMI-compliant mail clients
- **Historical trend analysis** — track report metrics over time
- **Multi-domain support** — manage reports for multiple domains from one dashboard
- **CSV export** — export report data for further analysis
- **Docker deployment** — containerized with Docker Compose

### Docker Compose Configuration

```yaml
version: '3.8'
services:
  viesti-reports:
    image: ghcr.io/antedebaas/viesti-reports:latest
    container_name: viesti-reports
    ports:
      - "8080:8080"
    environment:
      - IMAP_HOST=imap.example.com
      - IMAP_PORT=993
      - IMAP_USER=dmarc-reports@example.com
      - IMAP_PASSWORD=your-imap-password
      - IMAP_USE_TLS=true
      - DATABASE_URL=sqlite:///data/viesti.db
    restart: unless-stopped
    volumes:
      - viesti-data:/app/data
      - bimi-assets:/app/bimi

volumes:
  viesti-data:
  bimi-assets:
```

### BIMI Indicator Setup

```bash
# 1. Upload your brand logo (SVG format) to the BIMI assets volume
cp your-brand-logo.svg /path/to/bimi-assets/

# 2. Add BIMI DNS record:
# default._bimi.example.com. IN TXT "v=BIMI1; l=https://bimi.example.com/your-brand-logo.svg"

# 3. The Viesti-Reports server will serve the logo at the configured URL
```

### When to Use

Viesti-Reports is the best choice for organizations that need BIMI support alongside DMARC and TLS-RPT processing. Its multi-domain dashboard and export capabilities make it suitable for MSPs and organizations managing email security across many domains.

## 3. rpter (hannob/rpter)

**rpter** is a minimalist Rust-based CLI tool for parsing SMTP TLS reports from email messages. Unlike the web-based alternatives, rpter is designed for command-line use and automation pipelines — making it ideal for integration with monitoring systems, log aggregators, and CI/CD workflows.

### Key Features

- **CLI-first design** — parse reports from stdin, files, or mailboxes
- **Rust performance** — fast parsing with minimal resource usage
- **JSON output** — machine-readable output for integration with monitoring tools
- **Docker support** — available as a container image
- **Lightweight** — single binary, no database required

### Installation

```bash
# Install from crates.io
cargo install rpter

# Or use Docker
docker pull ghcr.io/hannob/rpter:latest
```

### Usage Examples

```bash
# Parse TLS reports from a maildir folder
rpter parse-maildir ~/Maildir/tls-reports/

# Parse a single JSON TLS report file
rpter parse-json report.json

# Pipe report data and output summary statistics
cat tls-report.json | rpter parse-json --summary

# Docker usage
docker run --rm -v ~/reports:/reports ghcr.io/hannob/rpter:latest parse-maildir /reports
```

### Integration with Monitoring

```bash
# Example: Parse reports and feed metrics to Prometheus pushgateway
rpter parse-maildir ~/Maildir/tls-reports/ --json |   jq -r '.[] | "\(.policy_type) \(.success_count) \(.failure_count)"' |   while read policy success failure; do
    echo "tls_rpt_success{policy="$policy"} $success" |       curl --data-binary @- http://pushgateway:9091/metrics/job/tls_rpt
  done
```

### When to Use

rpter is best suited for DevOps teams that want to integrate TLS report parsing into existing monitoring and alerting pipelines. Its CLI design and JSON output make it easy to chain with other tools like jq, grep, and monitoring agents.

## Setting Up Your Report Collection Infrastructure

Regardless of which tool you choose, you need a mail collection endpoint to receive TLS and DMARC reports. Here's a recommended setup:

### DNS Configuration

```dns
; DMARC record
_dmarc.example.com. IN TXT "v=DMARC1; p=reject; rua=mailto:dmarc-reports@example.com; ruf=mailto:dmarc-forensics@example.com"

; MTA-STS policy discovery
_mta-sts.example.com. IN TXT "v=STSv1; id=20260101"

; MTA-STS policy document (hosted at https://mta-sts.example.com/.well-known/mta-sts.txt)
; TLS Reporting record
_smtp._tls.example.com. IN TXT "v=TLSRPTv1; rua=mailto:tls-reports@example.com"
```

### MTA-STS Policy Document

```
version: STSv1
mode: enforce
mx: mx1.example.com
mx: mx2.example.com
max_age: 86400
```

### Report Processing Pipeline

```
Incoming Reports → IMAP Mailbox → Report Parser → Web Dashboard / Monitoring System
                                                              ↓
                                                  Alert on Policy Failures
                                                  Track TLS Adoption Trends
                                                  Monitor Certificate Issues
```

## Why Self-Host Your Email Security Reports?

Managing email security reports in-house provides several advantages over commercial platforms. First, you maintain **complete data ownership** — report data never leaves your infrastructure, which is critical for organizations handling sensitive communications or operating under strict data protection regulations like GDPR.

Second, self-hosted processing enables **deep integration** with your existing monitoring stack. You can correlate TLS failure spikes with infrastructure changes, feed report data into your SIEM for threat detection, or trigger automated alerts when certificate issues are detected.

Third, the **cost savings** are significant for organizations processing thousands of reports daily. Commercial DMARC analysis services typically charge $50-500/month depending on volume. Self-hosted solutions cost only the infrastructure to run a lightweight container.

For related reading, see our [MTA-STS and SMTP DANE guide](../2026-04-28-self-hosted-mta-sts-smtp-dane-email-security-guide-2026/) for configuring transport security policies, and our [email authentication deep dive](../self-hosted-dmarc-analysis-email-authentication-parsedmarc-opendmarc-g/) for understanding DMARC report structure. For mail server monitoring, check our [Postfix mail queue management guide](../2026-05-05-self-hosted-mail-queue-management-postfix-mailgraph-pflogsu/).

## FAQ

### What is SMTP TLS Reporting (TLS-RPT)?

SMTP TLS Reporting (RFC 8460) is a protocol that allows mail servers to send daily reports about the success or failure of TLS-encrypted connections to your domain. These reports help you identify TLS configuration issues, certificate problems, and mail servers that don't support encryption.

### How do I enable TLS reporting for my domain?

Add a DNS TXT record at `_smtp._tls.yourdomain.com` with the value `v=TLSRPTv1; rua=mailto:reports@yourdomain.com`. Mail servers that support TLS-RPT will send JSON-formatted reports to the specified address daily.

### What's the difference between DMARC and TLS-RPT?

DMARC reports focus on email authentication (SPF and DKIM results), telling you who is sending email claiming to be from your domain. TLS-RPT reports focus on transport security, telling you whether connections to your mail servers used encryption and whether certificates were valid.

### Can I use these tools for both DMARC and TLS reports?

Yes. DMARC Report Viewer and Viesti-Reports both process DMARC aggregate reports (XML format) and SMTP TLS reports (JSON format). rpter focuses primarily on TLS reports but can parse related data formats.

### Do I need a dedicated mail server to receive reports?

No. All three tools can connect to any IMAP mailbox. You can use a dedicated folder in your existing mail server or a free email provider to receive reports.

### How often are TLS reports delivered?

TLS reports are typically delivered once per day by each reporting organization. Major providers like Google, Microsoft, and Yahoo send reports every 24 hours. You may receive 10-50+ reports per day depending on your email volume.

### Is BIMI support important?

BIMI (Brand Indicators for Message Identification) allows your brand logo to appear in supporting mail clients alongside authenticated emails. If brand visibility in email is important to your organization, Viesti-Reports' built-in BIMI hosting is a significant advantage.

## Choosing the Right Tool

- **For simplicity**: DMARC Report Viewer provides the most straightforward setup — connect to IMAP and start viewing reports immediately.
- **For BIMI + multi-domain**: Viesti-Reports is the only option with built-in BIMI indicator hosting and multi-domain management.
- **For automation and pipelines**: rpter's CLI design and JSON output make it ideal for integration with monitoring systems and CI/CD workflows.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SMTP TLS Reporting — DMARC Report Viewer vs Viesti-Reports vs Rpter",
  "description": "Compare open-source tools for processing and visualizing SMTP TLS reports (RFC 8460) and DMARC aggregate reports — DMARC Report Viewer, Viesti-Reports, and rpter.",
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
