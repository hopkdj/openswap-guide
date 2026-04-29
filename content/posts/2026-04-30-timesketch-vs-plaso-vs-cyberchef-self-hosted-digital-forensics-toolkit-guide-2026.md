---
title: "Timesketch vs Plaso vs CyberChef: Self-Hosted Digital Forensics Toolkit Guide 2026"
date: 2026-04-30
tags: ["comparison", "guide", "self-hosted", "security", "forensics", "incident-response"]
draft: false
description: "Compare Timesketch, Plaso (log2timeline), and CyberChef — three essential open-source digital forensics tools for self-hosted incident response and evidence analysis."
---

Digital forensics has become a critical capability for every organization that manages its own infrastructure. When a security incident occurs, the ability to collect, analyze, and present digital evidence can mean the difference between a swift resolution and a prolonged breach. This guide compares three essential open-source digital forensics tools — **Timesketch**, **Plaso (log2timeline)**, and **CyberChef** — each serving a distinct role in the forensic analysis workflow.

All three tools are part of or closely aligned with Google's Open Source Digital Forensics and Incident Response ([OSDFIR](https://github.com/google/osdfir)) ecosystem. They are free, self-hosted, and Docker-deployable, making them accessible to security teams of any size.

## Why Self-Host Your Forensics Toolkit

Running forensic analysis tools on your own infrastructure offers several advantages over cloud-based alternatives:

- **Evidence chain of custody**: All data stays within your network, eliminating concerns about third-party access to sensitive evidence
- **No data egress costs**: Forensic artifacts can be massive — disk images, memory dumps, and log archives often total hundreds of gigabytes
- **Offline capability**: Investigations can proceed even when internet connectivity is unavailable or untrusted
- **Custom tooling**: Self-hosted tools can be extended with internal scripts, parsers, and integrations
- **Compliance requirements**: Many regulatory frameworks (SOC 2, ISO 27001, HIPAA) require forensic data to remain under direct organizational control

For teams that already self-host their [security monitoring stack](../2026-04-29-neuvector-vs-falco-vs-tetragon-container-runtime-security-guide-2026/), adding forensic tools to the same infrastructure is a natural extension.

## Tool Overview and Comparison

| Feature | Timesketch | Plaso (log2timeline) | CyberChef |
|---------|-----------|---------------------|-----------|
| **Primary Purpose** | Collaborative timeline analysis | Forensic timeline extraction | Data transformation and decoding |
| **Organization** | Google | Google / log2timeline | GCHQ |
| **GitHub Stars** | 3,319 | 2,057 | 34,718 |
| **Interface** | Web UI | Command-line | Web UI |
| **Collaboration** | Multi-user, real-time | Single-user | Single-user |
| **Data Sources** | Plaso output, CSV, JSON | Disk images, logs, registries, browsers | Raw data (text, binary, encoded) |
| **Timeline Support** | Full timeline visualization | Timeline extraction only | No timeline features |
| **Search/Filtering** | Full-text search, saved searches | No built-in search | No built-in search |
| **Export Formats** | CSV, JSON, PDF, OpenSearch | CSV, JSON, L2TCSV, dynamic | 400+ output formats |
| **Docker Support** | Official compose | Official Docker image | Official Docker image |
| **Best For** | Team investigations, timeline review | Evidence collection, parsing | Quick data analysis, decoding |

## Timesketch: Collaborative Forensic Timeline Analysis

Timesketch is a web-based tool for collaborative forensic timeline analysis. It allows multiple investigators to work on the same timeline simultaneously, annotate events, share findings, and build a narrative around the evidence.

### Key Features

- **Multi-user collaboration**: Multiple analysts can annotate the same timeline in real-time
- **Saved searches and views**: Create reusable search filters for common investigation patterns
- **Sketch sharing**: Export and import timelines between instances for cross-team collaboration
- **OpenSearch backend**: Full-text search across millions of events with near-instant response
- **REST API**: Integrate with other tools in your security stack
- **Story feature**: Build narrative reports combining timeline events, analysis notes, and visualizations

### Docker Compose Deployment

Timesketch uses a multi-container architecture with OpenSearch, PostgreSQL, and Redis as backend services. Here is the official Docker Compose configuration from the [Timesketch repository](https://github.com/google/timesketch):

```yaml
services:
  timesketch-web:
    container_name: timesketch-web
    image: us-docker.pkg.dev/osdfir-registry/timesketch/timesketch:latest
    environment:
      - NUM_WSGI_WORKERS=4
    restart: always
    command: timesketch-web
    volumes:
      - ./config/timesketch:/etc/timesketch/
      - ./upload:/usr/share/timesketch/upload/
      - ./logs:/var/log/timesketch/
    depends_on:
      opensearch:
        condition: service_healthy
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    ports:
      - "5000:5000"

  opensearch:
    container_name: timesketch-opensearch
    image: opensearchproject/opensearch:2
    environment:
      - discovery.type=single-node
      - plugins.security.disabled=true
    volumes:
      - opensearch-data:/usr/share/opensearch/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9200/_cluster/health"]
      interval: 10s
      timeout: 5s
      retries: 10

  postgres:
    container_name: timesketch-postgres
    image: postgres:16
    environment:
      - POSTGRES_USER=timesketch
      - POSTGRES_PASSWORD=timesketch
      - POSTGRES_DB=timesketch
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U timesketch"]
      interval: 10s
      timeout: 5s
      retries: 10

  redis:
    container_name: timesketch-redis
    image: redis:7
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 10

volumes:
  opensearch-data:
  postgres-data:
```

Deploy with:

```bash
mkdir -p config/timesketch upload logs
docker compose up -d
```

Access the web UI at `http://localhost:5000`. The default credentials are `dev/dev`.

### Typical Investigation Workflow

1. **Import data**: Upload a Plaso storage file (`.plaso`) or CSV timeline
2. **Explore**: Use the timeline view to browse events chronologically
3. **Search**: Filter by event type, timestamp range, hostname, or full-text search
4. **Annotate**: Tag events as relevant, add comments, and mark indicators of compromise
5. **Share**: Export the sketch or invite other analysts to collaborate
6. **Report**: Use the story feature to build an investigation narrative

## Plaso (log2timeline): Forensic Timeline Extraction Engine

Plaso is a Python-based forensic timeline extraction tool that converts various data sources into a unified timeline format. It is the engine that powers Timesketch's data ingestion pipeline, but it can also be used standalone for command-line forensic analysis.

### Key Features

- **100+ parsers**: Support for Windows event logs, registry hives, browser history, file system metadata, log files, and more
- **Super timeline**: Merge artifacts from multiple sources into a single chronological timeline
- **Filtering**: Apply event filters during extraction to reduce noise
- **Output formats**: Export to CSV, JSON, L2TCSV, dynamic format, or directly to Timesketch
- **Modular architecture**: Easy to add custom parsers for proprietary log formats

### Docker Deployment

Plaso provides an official Docker image through the OSDFIR registry:

```bash
docker pull us-docker.pkg.dev/osdfir-registry/timesketch/timesketch:latest
```

Plaso runs as a command-line tool within the Timesketch container, or you can run it standalone:

```bash
# Run log2timeline against a disk image
docker run --rm -v /evidence:/evidence \
  us-docker.pkg.dev/osdfir-registry/timesketch/timesketch:latest \
  log2timeline.py /evidence/output.plaso /evidence/disk-image.E01

# Run pinfo to inspect the resulting storage file
docker run --rm -v /evidence:/evidence \
  us-docker.pkg.dev/osdfir-registry/timesketch/timesketch:latest \
  pinfo.py /evidence/output.plaso
```

### Example: Extracting a Windows Forensic Timeline

```bash
# Create evidence directory
mkdir -p /evidence

# Mount or copy evidence files to /evidence

# Run log2timeline with workers for faster processing
log2timeline.py --workers 4 /evidence/windows-timeline.plaso /evidence/windows-disk.E01

# Filter to a specific time range
psort.py -o l2tcsv -w /evidence/timeline.csv \
  "date > '2026-04-01' AND date < '2026-04-30'" \
  /evidence/windows-timeline.plaso

# Import into Timesketch for collaborative analysis
psort.py -o timesketch --name "Windows Incident April 2026" \
  /evidence/windows-timeline.plaso
```

Plaso supports Evidence Format (E01), raw disk images, VMDK, VHD, and individual file collections. The tool automatically identifies file system types, parses registry hives, extracts browser artifacts, and processes Windows event logs — all in a single pass.

## CyberChef: The Cyber Swiss Army Knife

CyberChef is a web-based data transformation and analysis tool developed by GCHQ. It provides over 400 operations for encoding, decoding, encryption, compression, and data analysis — all running entirely in your browser (client-side, no data leaves your machine).

### Key Features

- **400+ operations**: Base64, hex, URL encoding, JWT decoding, XOR, regex, hash functions, and more
- **Recipe system**: Chain operations together into reusable analysis workflows
- **Client-side processing**: All data stays in the browser — nothing is sent to a server
- **Magic mode**: Automatically detect encoding and suggest decoding operations
- **File support**: Process files up to several hundred megabytes
- **Regex extraction**: Extract patterns like IP addresses, email addresses, and file paths from raw data

### Docker Deployment

CyberChef provides an official Docker image:

```bash
docker run --rm -p 8080:8080 mpepping/cyberchef:latest
```

Or use the official GCHQ image:

```bash
docker run --rm -p 8080:8080 ghcr.io/gchq/cyberchef:latest
```

Access the web UI at `http://localhost:8080`.

### Common Forensic Use Cases

**Decode Base64-encoded PowerShell commands:**

```
Input: powershell -enc UwB0AGEAcgB0AC0AUwBsAGUAZQBwACAALQBTAGUAYwBvAG4AZABzACAAMQAwAA==
Operation: From Base64 → To Text
Output: Start-Sleep -Seconds 10
```

**Extract IoCs from a log file:**

```
Input: Raw log data containing IP addresses, domains, and file hashes
Operation: Extract IP Addresses / Extract Domains / Extract MD5 / Extract SHA256
Output: Clean list of indicators of compromise
```

**Decode obfuscated JavaScript:**

```
Input: Obfuscated JS payload from a phishing email
Operation: From Hex → From Charcode → Beautify JavaScript
Output: Readable JavaScript source code
```

### Building and Saving Recipes

CyberChef recipes can be exported as URLs (with operations encoded in the fragment) or saved as JSON files. This allows teams to share standardized analysis workflows:

```json
{
  "category": "Forensics",
  "name": "Extract Email IoCs",
  "steps": [
    {"op": "Regular expression", "args": ["User defined", "[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+", true, true, false, false, false, false, "List matches"]},
    {"op": "To lowercase", "args": []},
    {"op": "Unique", "args": ["Line based"]}
  ]
}
```

## Choosing the Right Tool for Your Investigation

These three tools serve different stages of the forensic analysis workflow:

| Stage | Tool | Why |
|-------|------|-----|
| **Evidence Collection** | Plaso | Extracts timelines from raw disk images, memory dumps, and log files |
| **Timeline Analysis** | Timesketch | Visualizes and enables collaborative exploration of extracted timelines |
| **Data Decoding** | CyberChef | Decodes obfuscated payloads, extracts IoCs, and transforms raw data |
| **Reporting** | Timesketch | Built-in story feature for investigation narratives |
| **Quick Analysis** | CyberChef | Instant encoding/decoding without setup |

A typical investigation follows this pattern:

1. **Collect**: Use Plaso to extract a timeline from compromised systems
2. **Analyze**: Import the timeline into Timesketch for team collaboration
3. **Decode**: Use CyberChef to decode suspicious strings, payloads, or encoded commands found during analysis
4. **Report**: Build the investigation narrative in Timesketch with annotated events and findings

## Installation Comparison

| Aspect | Timesketch | Plaso | CyberChef |
|--------|-----------|-------|-----------|
| **Install Complexity** | High (4 services) | Low (single binary) | Low (single container) |
| **System Requirements** | 8 GB RAM, 4 CPU cores | 4 GB RAM, 2 CPU cores | 1 GB RAM, 1 CPU core |
| **Storage** | 20 GB+ (OpenSearch + PostgreSQL) | Depends on evidence size | Minimal (stateless) |
| **Docker Ready** | Yes (official compose) | Yes (official image) | Yes (official image) |
| **Linux Support** | Yes | Yes | Yes |
| **macOS Support** | Yes (Docker) | Yes (Homebrew) | Yes (Docker) |
| **Windows Support** | Yes (Docker) | Limited | Yes (Docker/browser) |

## Security Considerations

When self-hosting forensic tools, keep these security practices in mind:

- **Isolate evidence storage**: Keep forensic evidence on separate, write-protected volumes
- **Network segmentation**: Place forensic tools on an isolated network segment, separate from production systems
- **Access controls**: Implement role-based access to Timesketch sketches and evidence files
- **Audit logging**: Enable audit logging on all forensic tool access for chain-of-custody documentation
- **Encryption at rest**: Encrypt evidence volumes using LUKS or dm-crypt
- **Regular updates**: Keep all containers and dependencies patched — forensic tools process untrusted data that may contain exploits

For teams that also run [container runtime security monitoring](../2026-04-29-neuvector-vs-falco-vs-tetragon-container-runtime-security-guide-2026/), consider integrating forensic evidence collection with runtime security alerts to accelerate incident response.

## FAQ

### What is the difference between Timesketch and Plaso?

Plaso (log2timeline) is a forensic timeline **extraction** tool — it reads raw data sources like disk images, log files, and registry hives, and produces a structured timeline of events. Timesketch is a forensic timeline **analysis** tool — it visualizes timelines (often produced by Plaso), enables multi-user collaboration, and provides search, filtering, and annotation capabilities. They are complementary: Plaso generates the data, Timesketch helps you analyze it.

### Can I use Timesketch without Plaso?

Yes. Timesketch accepts timelines in multiple formats including CSV, JSON, and JSONL. While Plaso is the most common data source, you can import timelines from any tool that can export to these formats, including custom scripts, SIEM exports, or manual event lists.

### Is CyberChef safe for sensitive forensic data?

Yes. CyberChef runs entirely client-side in the browser. No data is ever sent to a server — all processing happens locally in your browser's JavaScript engine. When self-hosted via Docker, the entire application runs on your infrastructure with no external dependencies.

### How much disk space do I need for Timesketch?

Timesketch uses OpenSearch for indexing and PostgreSQL for metadata. A typical deployment requires 20 GB minimum for the database and search indices. The actual storage requirement scales with the volume of timeline data — a full Windows disk image timeline can easily exceed 10 GB after parsing and indexing.

### Can Plaso parse macOS and Linux artifacts?

Yes. Plaso supports forensic artifact extraction from Windows, macOS, and Linux systems. On macOS, it parses plist files, SQLite databases (Safari, Chrome, Messages), file system metadata, and system logs. On Linux, it processes syslog, auth.log, bash history, cron entries, and file system timestamps.

### How do I share Timesketch timelines with external investigators?

Timesketch supports exporting sketches as OpenSearch-compatible JSON files, which can be imported into another Timesketch instance. You can also export individual timelines as CSV or JSON for sharing. The sketch sharing feature allows you to invite specific users by email to collaborate on a timeline.

### What file formats does CyberChef support?

CyberChef supports any input that can be represented as text or binary data, including raw files, hex dumps, Base64-encoded strings, URL-encoded data, compressed archives (gzip, zip, bzip2), and encrypted payloads. The "Load file" operation lets you upload files directly from your local machine.

### Can I automate CyberChef recipes in a CI/CD pipeline?

While CyberChef is primarily a web UI tool, the underlying operations are available as a JavaScript library (`cyberchef-core`). You can embed CyberChef operations in Node.js scripts or use the REST API of a self-hosted instance to automate recipe execution. For fully automated forensic pipelines, consider using Plaso's command-line interface combined with psort.py for filtering and output.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Timesketch vs Plaso vs CyberChef: Self-Hosted Digital Forensics Toolkit Guide 2026",
  "description": "Compare Timesketch, Plaso (log2timeline), and CyberChef — three essential open-source digital forensics tools for self-hosted incident response and evidence analysis.",
  "datePublished": "2026-04-30",
  "dateModified": "2026-04-30",
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
