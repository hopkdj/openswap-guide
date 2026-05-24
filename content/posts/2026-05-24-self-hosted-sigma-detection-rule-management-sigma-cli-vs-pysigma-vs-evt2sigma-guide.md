---
title: "Self-Hosted Sigma Detection Rule Management: sigma-cli vs pySigma vs evt2sigma"
date: "2026-05-24"
tags: ["sigma-rules", "detection-engineering", "siem", "threat-detection", "sigma-cli", "pySigma", "security-operations", "self-hosted"]
draft: false
---

Sigma is the open standard for writing detection rules in a platform-agnostic format. Instead of maintaining separate rule sets for Splunk, Elastic, QRadar, and every other SIEM platform, security teams write detections once in Sigma format and convert them to the query language of their chosen platform. This approach dramatically reduces detection engineering effort and enables community rule sharing.

In this guide, we compare three open-source tools for managing, converting, and generating Sigma detection rules: **sigma-cli**, **pySigma**, and **evt2sigma**. Each serves a different role in the detection engineering workflow -- from rule validation and conversion to log-to-rule generation.

## What Is the Sigma Rule Format?

Sigma rules are YAML files that describe detection logic independent of any specific SIEM or log platform. A Sigma rule specifies:

- **Log source**: Which data source the rule applies to (Windows Event Logs, Linux audit logs, cloud trails, etc.)
- **Detection logic**: Field-value patterns, aggregation conditions, and filtering criteria
- **Severity and risk level**: How critical the detection is
- **MITRE ATT&CK mapping**: Which adversary techniques the rule detects
- **False positive guidance**: Known legitimate activities that may trigger the rule

The Sigma ecosystem provides conversion backends that translate these rules into native query languages -- Splunk SPL, Elastic Query, KQL, Azure Sentinel, and dozens more.

## sigma-cli: Command Line Interface for Sigma Rules

**sigma-cli** is the official command-line tool for working with Sigma rules. Built on top of pySigma, it provides a unified interface for converting, validating, and managing Sigma detection rules.

**GitHub:** [SigmaHQ/sigma-cli](https://github.com/SigmaHQ/sigma-cli) -- 192 stars, last updated May 2026

### How sigma-cli Works

sigma-cli loads Sigma rules from files or directories, validates their syntax against the Sigma specification, and converts them to backend-specific query formats using pySigma's conversion engine. It supports rule grouping, backend selection, and output customization.

### Installation

```bash
# pip install
pip install sigma-cli

# Or with backend plugins (recommended)
pip install sigma-cli pysigma-backend-splunk pysigma-backend-elasticsearch pysigma-backend-lucene
```

### Docker Deployment

```yaml
version: "3.8"
services:
  sigma-cli:
    image: python:3.12-slim
    container_name: sigma-converter
    restart: unless-stopped
    volumes:
      - ./sigma-rules:/sigma-rules:ro
      - ./output:/output
    entrypoint: ["/bin/sh", "-c"]
    command: |
      pip install --no-cache-dir sigma-cli \
        pysigma-backend-splunk \
        pysigma-backend-elasticsearch \
        pysigma-backend-lucene
      sigma convert -t splunk /sigma-rules/ -o /output/splunk_queries.txt
```

### Usage Examples

```bash
# Convert a single rule to Splunk SPL
sigma convert -t splunk -s rules/windows/process_creation/ \
  -o splunk_queries.txt

# Convert all rules to Elasticsearch Query DSL
sigma convert -t elasticsearch -s rules/ -o elastic_queries.json

# Validate rules without converting
sigma validate rules/

# List available backends
sigma list backends

# Convert with specific output format
sigma convert -t splunk -s rules/ --output-format json -o output.json

# Use a specific pipeline for rule preprocessing
sigma convert -t splunk -s rules/ -p windows-audit -o output.txt
```

### Key Features

- Official Sigma command-line interface
- Rule validation against the Sigma specification
- Multiple backend support (Splunk, Elastic, KQL, Lucene, and more)
- Pipeline system for rule preprocessing and normalization
- JSON and text output formats
- Directory-based rule management
- Plugin architecture for custom backends

### Limitations

- CLI-only -- no web interface or GUI
- Requires separate backend plugins for each target platform
- Rule management (versioning, collaboration) must be handled externally (e.g., Git)
- Limited built-in rule creation capabilities (primarily a converter)

## pySigma: Python Library for Sigma Rule Processing

**pySigma** is the core Python library that powers sigma-cli and other Sigma tools. It provides a programmatic API for parsing, validating, modifying, and converting Sigma rules. While sigma-cli is for command-line use, pySigma is for developers building custom Sigma integrations, web applications, or automated detection pipelines.

**GitHub:** [SigmaHQ/pySigma](https://github.com/SigmaHQ/pySigma) -- 556 stars, last updated May 2026

### How pySigma Works

pySigma parses Sigma YAML rule files into Python objects, validates them against the specification, and then applies backend-specific conversion logic to produce native query strings. The library is modular -- backends are separate packages that register with pySigma's plugin system.

### Installation

```bash
# Core library
pip install pysigma

# Backend plugins
pip install pysigma-backend-splunk
pip install pysigma-backend-elasticsearch
pip install pysigma-backend-sentinel
pip install pysigma-backend-defender

# For rule processing pipelines
pip install pysigma-pipeline-windows
pip install pysigma-pipeline-linux
```

### Python API Usage

```python
from sigma.collection import SigmaCollection
from sigma.backends.splunk import SplunkBackend

# Load rules from a directory
rules = SigmaCollection.load_ruleset(["rules/windows/"])

# Create a backend
backend = SplunkBackend()

# Convert all rules
for rule in rules:
    query = backend.convert(rule)
    print(f"Rule: {rule.title}")
    print(f"Query: {query}")
    print("---")
```

### Docker Deployment

```yaml
version: "3.8"
services:
  pysigma-api:
    image: python:3.12-slim
    container_name: pysigma-converter
    restart: unless-stopped
    volumes:
      - ./rules:/rules:ro
      - ./scripts:/scripts
    working_dir: /scripts
    entrypoint: ["/bin/sh", "-c"]
    command: |
      pip install --no-cache-dir pysigma \
        pysigma-backend-splunk \
        pysigma-backend-elasticsearch
      python converter.py /rules/ /output/
```

### Key Features

- Programmatic Sigma rule API for custom integrations
- Pluggable backend system (20+ backends available)
- Processing pipelines for rule transformation
- Rule validation and error reporting
- Support for Sigma specification v1 and v2
- Integration with CI/CD pipelines for automated rule testing
- Used by sigma-cli, Hayabusa, and other Sigma tools

### Limitations

- Library-only -- requires Python development to use
- No standalone CLI (use sigma-cli for command-line access)
- Backend plugins must be installed separately
- Learning curve for custom pipeline development

## evt2sigma: Log-to-Sigma Rule Generator

**evt2sigma** takes the opposite approach from sigma-cli and pySigma. Instead of converting existing Sigma rules to SIEM queries, it takes raw log entries and automatically generates Sigma detection rules from them. This is valuable when you encounter a novel attack pattern in your logs and want to quickly create a detection rule.

**GitHub:** [Neo23x0/evt2sigma](https://github.com/Neo23x0/evt2sigma) -- 107 stars

### How evt2sigma Works

evt2sigma analyzes log entries and extracts the key fields and values that characterize the event. It then generates a Sigma rule template with those fields as detection criteria. The generated rule serves as a starting point -- security engineers refine the logic, add MITRE ATT&CK mappings, and tune false positive conditions.

### Installation

```bash
# Clone and install
git clone https://github.com/Neo23x0/evt2sigma.git
cd evt2sigma
pip install -r requirements.txt

# Usage
python evt2sigma.py --input sample_event.json --output detection_rule.yml
```

### Docker Deployment

```yaml
version: "3.8"
services:
  evt2sigma:
    image: python:3.12-slim
    container_name: evt2sigma-generator
    restart: unless-stopped
    volumes:
      - ./events:/events:ro
      - ./rules:/rules
    working_dir: /app
    entrypoint: ["/bin/sh", "-c"]
    command: |
      pip install --no-cache-dir pyyaml
      python evt2sigma.py --input /events/ --output /rules/
```

### Key Features

- Automated Sigma rule generation from raw log entries
- Windows Event Log parsing and field extraction
- Template-based rule generation with standard Sigma structure
- Starting point for detection engineering workflows
- Reduces manual rule creation effort
- Integrates with incident response processes

### Limitations

- Less active development
- Generated rules require manual refinement
- Primarily focused on Windows Event Logs
- No built-in rule validation (use sigma-cli validate after generation)
- Limited backend support compared to sigma-cli

## Comparison Table

| Feature | sigma-cli | pySigma | evt2sigma |
|---------|-----------|---------|-----------|
| Primary Purpose | Rule conversion CLI | Python library | Rule generation from logs |
| Interface | Command line | Python API | Command line |
| Rule Conversion | Yes (20+ backends) | Yes (20+ backends) | No |
| Rule Generation | No | No | Yes (from logs) |
| Rule Validation | Yes | Yes (programmatic) | No |
| Processing Pipelines | Yes | Yes | No |
| Backend Plugins | Installable | Installable | N/A |
| CI/CD Integration | Yes (CLI) | Yes (library) | Limited |
| Active Development | Yes (May 2026) | Yes (May 2026) | Limited |
| Best For | Detection engineers | Developers/integrators | Incident response analysts |

## Why Self-Host Sigma Rule Management?

Detection engineering is a core security operations capability. Commercial SIEM platforms often lock detection logic into proprietary rule formats, making it difficult to share rules across organizations or migrate between platforms. Sigma breaks this lock-in by providing a vendor-neutral detection standard.

Self-hosting your Sigma toolchain gives you full control over rule conversion, validation, and deployment. You can integrate Sigma rules into your CI/CD pipeline, automatically testing new detections against historical log data before deploying them to production SIEM systems.

For security operations centers (SOCs), a self-hosted Sigma conversion pipeline enables rapid rule deployment across multiple SIEM platforms. Write a detection once in Sigma format, convert it to Splunk, Elastic, and Sentinel queries simultaneously, and deploy to all platforms in a single operation.

For incident responders, evt2sigma accelerates detection creation during active investigations. When you identify a novel attack pattern in event logs, generating a Sigma rule template in seconds rather than minutes means faster deployment of detection coverage.

For related security monitoring topics, see our [Suricata vs Snort vs Zeek IDS guide](../2026-04-18-suricata-vs-snort-vs-zeek-self-hosted-ids-ips-guide-2026/) for network-level detection and our [file integrity monitoring guide](../2026-05-06-self-hosted-file-integrity-monitoring-aide-ossec-tripwire-guide/) for endpoint security monitoring.

## Choosing the Right Tool

**Use sigma-cli** if you are a detection engineer who needs a command-line tool for converting, validating, and managing Sigma rules. It is the most practical tool for day-to-day Sigma rule operations.

**Use pySigma** if you are building custom Sigma integrations, web applications, or automated detection pipelines. The Python API enables programmatic rule processing that sigma-cli cannot provide.

**Use evt2sigma** if you need to quickly generate Sigma rule templates from raw log entries during incident response. It accelerates the initial rule creation step, though generated rules should be refined and validated with sigma-cli before deployment.

For a complete workflow, use all three tools together: evt2sigma to generate initial rule templates from incident logs, pySigma to build custom processing pipelines, and sigma-cli to validate and convert rules for deployment.

## FAQ

### What SIEM platforms does Sigma support?
Sigma supports 20+ query backends including Splunk SPL, Elasticsearch Query DSL, Microsoft Sentinel (KQL), Azure Log Analytics, Defender (KQL), QRadar AQL, Graylog, LogPoint, SumoLogic, AWS CloudWatch Logs, and many more. New backends are added regularly through the plugin system.

### How do I validate my Sigma rules before deploying them?
Use `sigma validate rules/` to check rule syntax against the Sigma specification. This catches YAML formatting errors, invalid field names, missing required fields, and unsupported detection patterns. Validation should be part of your CI/CD pipeline before any rule deployment.

### Can I write custom conversion backends for my SIEM?
Yes. pySigma's plugin architecture allows you to create custom backends for any query language. The backend implements a SigmaBackend class that defines field mappings, query templates, and aggregation handling. The SigmaHQ documentation includes a backend development guide.

### How do I manage Sigma rule versioning and collaboration?
Store Sigma rules in a Git repository. Each rule is a standalone YAML file, making Git's diff and merge operations work naturally. Use pull requests for rule review, and CI/CD pipelines for automated validation and conversion before merging. The SigmaHQ community repository (github.com/SigmaHQ/sigma) follows this pattern.

### Are Sigma rules compatible with all log sources?
Sigma rules specify log source requirements (product, service, category, definition). A rule written for Windows Security Event Logs requires Windows log sources. A rule for Linux auditd requires auditd log sources. The conversion backend maps Sigma fields to the target platform's field names for the specified log source.

### How does Sigma compare to YARA rules?
Sigma and YARA serve different purposes. YARA rules detect malicious files based on byte patterns and string matching. Sigma rules detect suspicious activity in log data based on field-value patterns. They are complementary -- YARA for file-based detection, Sigma for log-based detection. Many security operations use both.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Sigma Detection Rule Management: sigma-cli vs pySigma vs evt2sigma",
  "description": "Compare three open-source Sigma rule tools for detection engineering -- CLI conversion, Python library integration, and automated rule generation from log entries.",
  "datePublished": "2026-05-24",
  "dateModified": "2026-05-24",
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
