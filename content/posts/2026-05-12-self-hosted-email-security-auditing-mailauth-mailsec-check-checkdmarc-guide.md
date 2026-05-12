---
title: "Self-Hosted Email Security Auditing: mailauth vs mailsec-check vs checkdmarc"
date: "2026-05-12"
tags: ["email", "security", "dmarc", "spf", "dkim", "auditing", "self-hosted"]
draft: false
---

Email authentication is the first line of defense against phishing, spoofing, and business email compromise. SPF, DKIM, and DMARC form the core triad of email authentication, but properly configuring and auditing these records across multiple domains is error-prone. Self-hosted email security auditing tools automate the validation process, providing comprehensive reports on your domain's email authentication posture.

This guide compares three open-source email security auditing tools: **mailauth** by Postalsys, **mailsec-check** by Foxcpp, and **checkdmarc** by Domain Awareness. Each tool validates SPF, DKIM, DMARC, and related security records, but they differ in scope, output format, and integration capabilities.

## Why Self-Host Email Security Auditing?

Email authentication failures are the root cause of most phishing successes. A misconfigured SPF record, a missing DKIM signature, or an incorrect DMARC policy can allow attackers to send email appearing to come from your domain. Regular auditing catches these misconfigurations before attackers exploit them.

Self-hosting auditing tools means you can run them on a schedule (cron), integrate them into CI/CD pipelines for domain configuration changes, and store historical audit data internally — rather than relying on third-party web tools that may log your domain information. For organizations managing dozens of domains, automated self-hosted auditing is essential for maintaining consistent email security posture.

For broader email infrastructure management, see our [complete email server guide](../self-hosted-email-server-postfix-dovecot-rspamd-complete-guide-2026/), [email alias management](../2026-04-20-simplelogin-vs-anonaddy-vs-forwardemail-self-hosted-email-alias-guide-2026/), and [email archiving comparison](../2026-04-18-self-hosted-email-archiving-mailpiler-dovecot-stalwart-guide-2026/).

## Comparison Overview

| Feature | mailauth | mailsec-check | checkdmarc |
|---------|----------|---------------|------------|
| **Developer** | Postalsys | Foxcpp | DomainAwareness |
| **License** | MIT | Apache-2.0 | Apache-2.0 |
| **GitHub Stars** | 141 | 68 | 1,100+ |
| **Language** | Node.js | Go | Python |
| **SPF Validation** | Full (macros, includes, redirects) | Full | Full (with DNS resolution) |
| **DKIM Validation** | DNS record check | DNS record check | DNS record check |
| **DMARC Validation** | Full policy analysis | Full policy analysis | Full + aggregate report analysis |
| **MTA-STS Check** | Yes | Yes | No |
| **TLS-RPT Check** | Yes | Yes | No |
| **BIMI Check** | Yes | No | Yes |
| **ARC Validation** | Yes | No | No |
| **Output Format** | JSON, HTML report | JSON, plain text | JSON, CSV, CLI |
| **DNSSEC Aware** | Yes | Yes | Yes |
| **Bulk Domain Audit** | Via scripting | Via scripting | Native bulk mode |
| **Docker Image** | Community | Community | Official |

## mailauth (Postalsys)

mailauth is a comprehensive email authentication checking tool by Postalsys. It validates the full spectrum of email security records: SPF, DKIM, DMARC, MTA-STS, TLS-RPT, BIMI, and ARC. It is the most feature-complete tool for email security auditing.

### Key Features

- **Comprehensive protocol coverage**: Validates SPF, DKIM, DMARC, MTA-STS, TLS-RPT, BIMI, and ARC in a single check
- **Deep SPF analysis**: Resolves SPF includes, redirects, and macros, with accurate DNS query counting
- **MTA-STS policy verification**: Fetches and validates MTA-STS policies from the `.well-known` endpoint
- **ARC chain validation**: Checks Authenticated Received Chain signatures for forwarded email integrity
- **DNS tree walk**: Follows DMARC DNS Tree Walk per the updated DMARC specification
- **JSON output**: Machine-readable results suitable for automation and CI/CD integration

### Installation and Usage

```bash
# Install via npm
npm install -g mailauth

# Check a single domain
mailauth check example.com

# Check with JSON output
mailauth check example.com --json > audit.json

# Check from file (multiple domains)
mailauth check --file domains.txt

# Check specific sender address
mailauth check sender@example.com --sender
```

### Docker Compose for Scheduled Auditing

```yaml
version: "3.8"

services:
  mailauth:
    image: node:20-alpine
    container_name: mailauth
    volumes:
      - ./scripts:/opt/scripts
      - ./results:/opt/results
    working_dir: /opt/scripts
    entrypoint: ["sh", "-c", "npm install -g mailauth && /opt/scripts/audit.sh"]
    restart: "no"

  # Optional: Schedule with cron
  cron-scheduler:
    image: mcuadros/ofelia:latest
    container_name: mailauth-cron
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./ofelia.ini:/etc/ofelia/config.ini:ro
    restart: unless-stopped
```

### Audit Script

```bash
#!/bin/sh
# audit.sh - Run mailauth check for all domains

DOMAINS="example.com example.org example.net"
RESULTS_DIR="/opt/results"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)

for domain in $DOMAINS; do
  echo "Checking $domain..."
  mailauth check "$domain" --json > "$RESULTS_DIR/${domain}_${TIMESTAMP}.json"
done

echo "Audit complete. Results in $RESULTS_DIR"
```

## mailsec-check

mailsec-check is a Go-based email security analysis tool that provides a lightweight, fast alternative for checking email authentication records. It focuses on the core protocols: SPF, DKIM, DMARC, MTA-STS, and TLS-RPT.

### Key Features

- **Fast execution**: Compiled Go binary with minimal startup overhead
- **Clean JSON output**: Structured results with severity levels for each finding
- **MTA-STS and TLS-RPT**: Validates both email transport security protocols
- **Single binary**: No runtime dependencies — just download and run
- **CI/CD friendly**: Exit codes indicate pass/fail status for automated pipelines

### Installation and Usage

```bash
# Download binary from GitHub releases
curl -sL https://github.com/foxcpp/mailsec-check/releases/latest/download/mailsec-check-linux-amd64 -o mailsec-check
chmod +x mailsec-check

# Check a domain
./mailsec-check example.com

# JSON output
./mailsec-check --json example.com

# Check with custom DNS resolver
./mailsec-check --dns-server 1.1.1.1 example.com

# Verbose output with all details
./mailsec-check --verbose example.com
```

### Docker Deployment

```yaml
version: "3.8"

services:
  mailsec-check:
    image: golang:1.22-alpine
    container_name: mailsec-check
    volumes:
      - ./domains.txt:/domains.txt:ro
      - ./results:/results
    entrypoint: >
      sh -c "
        cd /tmp && go install github.com/foxcpp/mailsec-check@latest &&
        while IFS= read -r domain; do
          echo "Checking \$domain..."
          mailsec-check --json \$domain > /results/\$domain.json
        done < /domains.txt
      "
    restart: "no"
```

## checkdmarc

checkdmarc is a Python-based domain security analysis tool that has become the most widely adopted email security auditor. It validates SPF, DKIM, DMARC, and BIMI records with DNSSEC awareness and provides detailed reports.

### Key Features

- **Most popular**: Over 1,100 GitHub stars and widely used in production environments
- **BIMI support**: Validates Brand Indicators for Message Identification records
- **DNSSEC validation**: Checks whether DNS records are properly signed
- **Aggregate report analysis**: Parses DMARC aggregate reports to identify authentication failures
- **Python library**: Can be imported and used programmatically in Python scripts
- **Multiple output formats**: JSON, CSV, and CLI output

### Installation and Usage

```bash
# Install via pip
pip install checkdmarc

# Check a single domain
checkdmarc example.com

# JSON output
checkdmarc --json example.com > audit.json

# Check multiple domains
checkdmarc example.com example.org example.net

# Save results as CSV
checkdmarc --csv domains.csv example.com example.org

# Parse DMARC aggregate report
checkdmarc --dmarc-report-file report.xml
```

### Docker Compose for Scheduled Auditing

```yaml
version: "3.8"

services:
  checkdmarc:
    image: ghcr.io/domainawareness/checkdmarc:latest
    container_name: checkdmarc
    volumes:
      - ./domains.txt:/domains.txt:ro
      - ./results:/results
    entrypoint: >
      sh -c "
        while IFS= read -r domain; do
          echo "Checking \$domain..."
          checkdmarc --json \$domain > /results/\$domain.json
        done < /domains.txt
      "
    restart: "no"
```

### Python Integration Example

```python
import checkdmarc
import json

domains = ["example.com", "example.org"]
results = {}

for domain in domains:
    try:
        result = checkdmarc.check_domains([domain])
        results[domain] = result
    except checkdmarc.DNSException as e:
        print(f"DNS error for {domain}: {e}")
    except checkdmarc.CheckException as e:
        print(f"Check error for {domain}: {e}")

# Save comprehensive report
with open("email_security_report.json", "w") as f:
    json.dump(results, f, indent=2, default=str)

print(f"Audited {len(results)} domains")
```

## Choosing the Right Email Security Auditor

- **Use mailauth** when you need the most comprehensive protocol coverage including ARC, MTA-STS, TLS-RPT, and BIMI in a single tool. Its Node.js ecosystem makes it easy to integrate with existing JavaScript/TypeScript tooling.
- **Use mailsec-check** when you need a fast, lightweight tool with minimal dependencies. Its compiled Go binary is ideal for CI/CD pipelines and container environments where startup time matters.
- **Use checkdmarc** when you need the most widely tested and supported tool with the largest community. Its Python library integration and DMARC report analysis capabilities make it ideal for programmatic use.

For email infrastructure hardening, also check our [email authentication guide](../2026-05-18-opendkim-vs-rspamd-vs-opendmarc-email-authentication-guide/) and [SMTP milter management](../2026-05-10-self-hosted-smtp-milter-management-milter-manager-rspamd-opendkim-guide/).

## FAQ

### What is the difference between SPF, DKIM, and DMARC?

SPF (Sender Policy Framework) specifies which mail servers are authorized to send email for your domain via DNS TXT records. DKIM (DomainKeys Identified Mail) adds a cryptographic signature to outgoing email headers that receivers can verify against a public key in DNS. DMARC (Domain-based Message Authentication, Reporting, and Conformance) ties SPF and DKIM together, telling receivers what to do when authentication fails (none, quarantine, or reject) and providing reporting on authentication results.

### Why do I need to audit email authentication records regularly?

DNS records can change due to misconfigurations, infrastructure changes, or expired certificates. A broken SPF record can cause legitimate email to bounce. A missing DKIM key can cause emails to land in spam. A DMARC policy set to "reject" with misaligned SPF/DKIM can reject all your outbound email. Regular audits catch these issues before they impact deliverability.

### What is MTA-STS and should I deploy it?

MTA-STS (SMTP MTA Strict Transport Security) is a policy mechanism that tells sending mail servers to require TLS encryption when delivering email to your domain. It prevents downgrade attacks where an attacker intercepts and strips TLS from email connections. If your mail server supports TLS, deploying MTA-STS is a recommended best practice.

### What is BIMI and is it worth implementing?

BIMI (Brand Indicators for Message Identification) allows you to display your brand logo in supporting email clients when your domain passes DMARC authentication. It requires a valid DMARC policy of "quarantine" or "reject," a verified VMC (Verified Mark Certificate), and a properly formatted SVG logo. While not essential for security, BIMI improves brand recognition and can increase email open rates.

### How often should I run email security audits?

For most organizations, weekly automated audits are sufficient. Run audits after any DNS changes, mail server migrations, or third-party email service provider changes. For high-security environments, daily audits with automated alerting on policy changes are recommended. Integrate audits into your CI/CD pipeline if you manage DNS through infrastructure-as-code tools.

### What should I do if an audit finds a misconfiguration?

First, determine the severity: a missing DMARC record is lower priority than a broken SPF record causing email bounces. Use the tool's detailed output to identify the specific DNS record causing the issue. Verify the fix by re-running the audit before and after making DNS changes. Allow time for DNS propagation (TTL-dependent) before confirming the fix.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Email Security Auditing: mailauth vs mailsec-check vs checkdmarc",
  "description": "Compare self-hosted email security auditing tools: mailauth, mailsec-check, and checkdmarc for validating SPF, DKIM, DMARC, and more.",
  "datePublished": "2026-05-12",
  "dateModified": "2026-05-12",
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
