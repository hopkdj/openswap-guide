---
title: "Self-Hosted Email Header Analysis — Email Header Analyzer vs mailMeta vs Headmail"
date: "2026-05-13"
tags: ["email-security", "forensics", "email-analysis", "threat-intelligence"]
draft: false
---

Email header analysis is a critical skill for security teams, incident responders, and email administrators. Every email carries a wealth of metadata in its headers — routing paths, authentication results, server timestamps, and originating IP addresses. Self-hosted email header analysis tools allow you to parse, visualize, and investigate this metadata without sending potentially sensitive email data to external online analyzers.

## Why Analyze Email Headers?

Email headers contain the forensic trail of every message. By analyzing headers, you can:

- **Identify phishing and spoofing attempts** — Check SPF, DKIM, and DMARC authentication results to detect forged sender addresses
- **Trace email routing paths** — Follow the Received headers to map the path an email took from sender to recipient
- **Detect relay abuse** — Identify if your mail server was used as an open relay for spam
- **Investigate delivery delays** — Compare timestamps between hop servers to pinpoint bottlenecks
- **Verify email authenticity** — Cross-reference originating IPs with known malicious ranges

## Email Header Analyzer

The Email Header Analyzer by CyberDefenders is a web-based tool designed for digital forensics and incident response. It parses raw email headers and presents them in a structured, human-readable format with visual timeline representations.

**Key features:**
- Visual timeline of email routing with hop-by-hop breakdown
- SPF, DKIM, and DMARC result parsing and validation
- IP address geolocation and reputation checking
- MIME structure decoding for attachment analysis
- Support for raw eml file uploads
- Self-hostable via Docker

**Docker Compose deployment:**
```yaml
version: "3.8"
services:
  email-header-analyzer:
    image: ghcr.io/cyberdefenders/email-header-analyzer:latest
    container_name: email-header-analyzer
    ports:
      - "8080:8080"
    environment:
      - TZ=UTC
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

**Configuration:**
The tool requires minimal configuration. For production deployments, add a reverse proxy with TLS termination:

```nginx
server {
    listen 443 ssl http2;
    server_name headers.example.com;

    ssl_certificate /etc/ssl/certs/headers.crt;
    ssl_certificate_key /etc/ssl/private/headers.key;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Email Header Analyzer is ideal for security teams that need a visual, timeline-based interface for investigating suspicious emails during incident response.

## mailMeta

mailMeta is a forensics-focused email analysis tool that specializes in detecting spoofed emails and extracting metadata for investigation purposes. It provides a command-line interface with detailed parsing of authentication headers and routing information.

**Key features:**
- Deep SPF/DKIM/DMARC analysis with pass/fail verdicts
- Header injection detection — identifies forged or modified headers
- Timeline reconstruction from Received header timestamps
- IP reputation integration for originating addresses
- Export results to JSON for SIEM integration
- Lightweight CLI tool with no external dependencies

**Installation:**
```bash
git clone https://github.com/gr33nm0nk2802/mailMeta.git
cd mailMeta
pip install -r requirements.txt
python mailmeta.py --file suspicious_email.eml
```

**Sample output:**
```
=== mailMeta Email Analysis ===
From: attacker@spoofed-domain.com
SPF: FAIL (sender IP 203.0.113.50 not authorized)
DKIM: FAIL (no valid signature found)
DMARC: FAIL (policy: reject)
Received Chain:
  [1] 2024-01-15 08:23:41 UTC - mail.spoofed-domain.com (203.0.113.50)
  [2] 2024-01-15 08:23:45 UTC - mx1.example.com (198.51.100.10)
  [3] 2024-01-15 08:23:47 UTC - internal-mail.example.com (10.0.1.25)
Alert: SPF/DKIM/DMARC all failed -- likely spoofed
```

**Docker deployment:**
```yaml
version: "3.8"
services:
  mailmeta:
    image: python:3.11-slim
    container_name: mailmeta
    working_dir: /app
    volumes:
      - ./mailmeta:/app
      - ./emails:/emails
    command: python mailmeta.py --file /emails/suspicious.eml --output /app/results
    restart: "no"
```

mailMeta is best suited for incident responders who prefer a CLI-driven workflow and need to integrate email analysis results into automated investigation pipelines.

## Headmail

Headmail is a lightweight, modern email header analysis tool that provides a clean web interface for parsing and visualizing email headers. It focuses on simplicity and ease of use while still providing comprehensive header parsing.

**Key features:**
- Clean, modern web interface for header analysis
- Automatic detection of suspicious patterns (missing authentication, relay chains)
- Visual hop-by-hop routing diagram
- Support for drag-and-drop eml file uploads
- Copy-paste raw header input for quick analysis
- No external API dependencies — fully offline capable

**Docker Compose deployment:**
```yaml
version: "3.8"
services:
  headmail:
    build: .
    container_name: headmail
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - PORT=3000
    restart: unless-stopped
```

**Build from source:**
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --production
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]
```

Headmail is the best choice for teams that want a simple, no-fuss web interface for quick email header checks without complex setup or external dependencies.

## Comparison Table

| Feature | Email Header Analyzer | mailMeta | Headmail |
|---------|----------------------|----------|----------|
| Interface | Web-based | CLI | Web-based |
| SPF/DKIM/DMARC | Full parsing | Deep analysis with verdicts | Basic parsing |
| Visual Timeline | Yes | Text-based | Yes (routing diagram) |
| IP Geolocation | Built-in | Via integration | No |
| File Upload | eml files | eml or raw headers | eml or paste or drag-drop |
| Docker Support | Yes | Yes | Yes |
| Offline Capable | Yes | Yes | Yes |
| SIEM Export | No | JSON output | No |
| Best For | IR teams, visual analysis | CLI automation, forensics | Quick checks, ease of use |
| Stars | 695+ | 172+ | 41+ |
| License | MIT | MIT | MIT |

## Why Self-Host Email Header Analysis Tools?

When investigating phishing emails or suspicious messages, you are handling potentially sensitive communication data. Using online email header analyzers means sending raw email headers — including recipient addresses, internal server names, and routing information — to third-party services. This creates privacy and compliance risks, especially for organizations handling regulated data.

Self-hosted email analysis tools keep all investigation data within your network boundary. This is essential for organizations subject to GDPR, HIPAA, or other data protection regulations that restrict sharing of email metadata with external services.

Additionally, self-hosted tools work in air-gapped environments where internet access is restricted — a common scenario in government, defense, and critical infrastructure sectors where email-based threats must be investigated without external connectivity.

For email authentication setup, see our [MTA-STS and DANE guide](../2026-04-28-self-hosted-mta-sts-smtp-dane-email-security/). For mail server management, check our [Postal vs Stalwart comparison](../2026-04-26-postal-vs-stalwart-vs-haraka-self-hosted-smtp/). For milter integration, our [SMTP milter management guide](../2026-05-10-self-hosted-smtp-milter-management-milter-manager-rspamd-opendkim/) covers filtering at the MTA level.


## Integration with Security Operations Workflows

Email header analysis tools become significantly more powerful when integrated into broader security operations workflows rather than operating as standalone investigation utilities. The right integration approach transforms manual header inspection into an automated threat detection capability.

**SIEM enrichment** is the most common integration pattern. When your email gateway flags a suspicious message, automated workflows can extract the raw headers, run them through a CLI-based tool like mailMeta, and push the parsed results into your SIEM as structured fields. This enables correlation rules that alert on specific patterns -- for example, emails that fail all three authentication checks (SPF, DKIM, and DMARC) from domains not previously seen in your environment.

**SOAR playbook integration** takes automation further by connecting header analysis to automated response actions. A typical playbook might: extract headers from the flagged email, run the analysis tool, check the originating IP against threat intelligence feeds, and if the confidence score exceeds a threshold, automatically quarantine the message, block the sender domain at the gateway, and create an incident ticket with the analysis results attached.

**Threat intelligence feed correlation** extends header analysis by cross-referencing extracted indicators (IP addresses, domains, message IDs) with threat intelligence platforms. Many self-hosted analysis tools can be scripted to query internal threat intelligence databases after parsing headers, enriching the analysis with historical context about known malicious infrastructure.

**Email gateway pre-filtering** uses lightweight header analysis to reject suspicious messages before they reach user mailboxes. By deploying a header analysis tool as a pre-delivery filter, you can automatically quarantine messages that exhibit multiple spoofing indicators -- failed authentication combined with suspicious routing patterns or originating IPs in known botnet ranges.

For organizations building mature security operations capabilities, integrating email header analysis into automated workflows reduces investigation time from minutes to seconds and ensures consistent analysis quality across all flagged messages regardless of analyst experience level.

## FAQ

### What information can email headers reveal about a phishing attempt?

Email headers show the true origin of a message, regardless of what the From field displays. By examining Received headers, you can trace the actual path the email took. SPF, DKIM, and DMARC results tell you whether the sender is authorized to send from the claimed domain. Mismatches between the visible sender and the actual originating IP are strong indicators of spoofing.

### How do I extract raw email headers from my email client?

In most email clients: Gmail -- open the email, click the three-dot menu, select Show original. Outlook -- open the email, go to File and then Properties, look at Internet headers. Thunderbird -- open the email, go to View and then Headers and then All. The raw headers can then be pasted into any self-hosted analysis tool.

### Can email header analysis detect Business Email Compromise (BEC)?

Header analysis alone cannot fully detect BEC attacks, since BEC often uses legitimate credentials and domains. However, it can reveal indicators such as unusual routing paths, missing authentication results, or emails originating from unexpected geographic locations. Header analysis should be combined with content analysis and user behavior monitoring for comprehensive BEC detection.

### What is the difference between SPF, DKIM, and DMARC in email headers?

SPF (Sender Policy Framework) verifies that the sending server IP address is authorized to send mail for the domain. DKIM (DomainKeys Identified Mail) uses cryptographic signatures to verify that the email content was not modified in transit. DMARC (Domain-based Message Authentication) specifies what receivers should do when SPF or DKIM checks fail and provides reporting. All three results appear in email headers as Authentication-Results fields.

### Are self-hosted email header analysis tools suitable for SOC teams?

Yes. Self-hosted tools provide the same analytical capabilities as online analyzers while keeping sensitive email data within your SOC infrastructure. mailMeta even supports JSON output for SIEM integration, allowing automated enrichment of security alerts with email header analysis results.

### How do I automate email header analysis for high-volume investigation?

For high-volume environments, CLI-based tools like mailMeta can be integrated into automated pipelines. You can set up a mail rule that forwards suspicious emails to a dedicated mailbox, then run a script that polls the mailbox, extracts headers, runs the analysis tool, and stores results in your investigation database.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Email Header Analysis -- Email Header Analyzer vs mailMeta vs Headmail",
  "description": "Compare self-hosted email header analysis tools for security forensics and phishing investigation. Covers Email Header Analyzer, mailMeta, and Headmail.",
  "datePublished": "2026-05-13",
  "dateModified": "2026-05-13",
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
