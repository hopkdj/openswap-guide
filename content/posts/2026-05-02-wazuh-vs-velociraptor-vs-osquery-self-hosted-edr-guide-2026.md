---
title: "Wazuh vs Velociraptor vs Osquery: Self-Hosted EDR & Endpoint Security Guide 2026"
date: 2026-05-02
tags: ["comparison", "guide", "self-hosted", "security", "edr", "endpoint-detection", "wazuh", "velociraptor", "osquery"]
draft: false
description: "Compare Wazuh, Velociraptor, and Osquery for self-hosted endpoint detection and response (EDR). Complete deployment guide with Docker configs, detection rules, and incident response workflows."
---

Endpoint Detection and Response (EDR) platforms like CrowdStrike Falcon, Microsoft Defender for Endpoint, and SentinelOne cost $50-$150 per endpoint per year — and that pricing assumes you are comfortable sending every process execution, file access, and network connection from your servers to a vendor's cloud. For organizations with strict data sovereignty requirements, regulated workloads, or simply a preference for keeping security telemetry on-premises, self-hosted EDR platforms provide an alternative.

In this guide, we compare three open-source platforms that deliver EDR-class capabilities without sending telemetry off-premises: **Wazuh** (15,445 stars, a unified XDR and SIEM platform), **Velociraptor** (3,935 stars, a digital forensics and incident response tool from Rapid7), and **Osquery** (23,236 stars, a SQL-based endpoint instrumentation engine from Meta). While Velociraptor and Osquery were previously covered in a threat hunting context, this article focuses specifically on their EDR capabilities — real-time detection, automated response, and continuous endpoint monitoring.

## What Makes EDR Different from Traditional Antivirus?

Traditional antivirus relies on signature matching — comparing files against a database of known malware hashes. EDR goes further:

- **Behavioral monitoring**: Track process creation, file modifications, registry changes, and network connections in real time.
- **Detection rules**: Write custom logic to flag suspicious patterns — a PowerShell downloading and executing a script, a service spawning a reverse shell, or a database process connecting to an external IP.
- **Automated response**: Isolate compromised endpoints, kill malicious processes, quarantine files, and block network connections without human intervention.
- **Forensic timeline**: Reconstruct the full attack chain — what happened first, how the attacker moved laterally, and what data was accessed.

Self-hosted EDR platforms deliver all of these capabilities while keeping every piece of telemetry within your infrastructure.

## Quick Comparison Table

| Feature | Wazuh | Velociraptor | Osquery |
|---|---|---|---|
| **Architecture** | Agent + Manager + Indexer | Server + Agents (VQL) | Daemon + TLS Server + Fleet manager |
| **Primary Focus** | XDR + SIEM + compliance | Digital forensics + IR | Endpoint instrumentation + querying |
| **Detection Engine** | Decoders + rules (XML) | VQL queries (YAML) | SQL queries (packs) |
| **Real-time Monitoring** | Yes (syscheck, log analysis) | Yes (event monitoring) | Yes (scheduled queries) |
| **Automated Response** | Yes (active response scripts) | Limited (via VQL actions) | Via Fleet/Orbit (scripts) |
| **File Integrity Monitoring** | Yes (built-in) | Via VQL queries | Via osquery tables |
| **Vulnerability Detection** | Yes (CVE database built-in) | Via VQL (external feeds) | Via osquery + external feeds |
| **Compliance Frameworks** | PCI-DSS, HIPAA, GDPR, NIST | Custom (VQL) | Custom (SQL packs) |
| **Agent Languages** | C | Go | C++ |
| **Docker Deployment** | Official compose | Official compose | Fleet server compose |
| **GitHub Stars** | 15,445 | 3,935 | 23,236 |
| **Last Update** | April 2026 | April 2026 | April 2026 |

## Wazuh: The Unified Security Platform

Wazuh is the most comprehensive self-hosted EDR platform available. It combines endpoint detection (via agents on every managed host), log analysis (via its manager), vulnerability detection (via CVE feed integration), and compliance monitoring (via built-in policy checks) into a single stack.

Wazuh's detection rules use a signature-like language in XML: rules match log patterns, decode fields, and trigger alerts at configurable severity levels. Its active response system can automatically block attacking IPs, quarantine files, or run custom remediation scripts when threats are detected.

### Wazuh Docker Compose Deployment

Wazuh provides an official Docker Compose file that deploys the full stack — manager, indexer, and dashboard:

```yaml
version: "3.8"

services:
  wazuh-manager:
    image: wazuh/wazuh-manager:4.9.0
    container_name: wazuh-manager
    hostname: wazuh-manager
    ports:
      - "1514:1514"
      - "1515:1515"
      - "514:514/udp"
      - "55000:55000"
    environment:
      - INDEXER_URL=https://wazuh-indexer:9200
      - INDEXER_USERNAME=admin
      - INDEXER_PASSWORD=YOUR_SECURE_PASSWORD
    volumes:
      - wazuh-manager-data:/var/ossec/data
      - wazuh-manager-logs:/var/ossec/logs
      - wazuh-manager-etc:/var/ossec/etc
    restart: unless-stopped

  wazuh-indexer:
    image: wazuh/wazuh-indexer:4.9.0
    container_name: wazuh-indexer
    hostname: wazuh-indexer
    ports:
      - "9200:9200"
    environment:
      - OPENSEARCH_JAVA_OPTS=-Xms1g -Xmx1g
      - bootstrap.memory_lock=true
    volumes:
      - wazuh-indexer-data:/var/lib/wazuh-indexer
      - wazuh-indexer-config:/usr/share/wazuh-indexer/opensearch.yml
    ulimits:
      memlock:
        soft: -1
        hard: -1
      nofile:
        soft: 65536
        hard: 65536
    restart: unless-stopped

  wazuh-dashboard:
    image: wazuh/wazuh-dashboard:4.9.0
    container_name: wazuh-dashboard
    hostname: wazuh-dashboard
    ports:
      - "443:443"
    environment:
      - INDEXER_USERNAME=admin
      - INDEXER_PASSWORD=YOUR_SECURE_PASSWORD
    depends_on:
      - wazuh-indexer
      - wazuh-manager
    restart: unless-stopped

volumes:
  wazuh-manager-data:
  wazuh-manager-logs:
  wazuh-manager-etc:
  wazuh-indexer-data:
  wazuh-indexer-config:
```

Write a custom detection rule in `/var/ossec/etc/rules/local_rules.xml`:

```xml
<group name="local,syslog,">
  <rule id="100100" level="10">
    <decoded_as>json</decoded_as>
    <field name="process.name">powershell.exe</field>
    <field name="process.command_line">\.Invoke-Expression</field>
    <description>Potential PowerShell code execution detected</description>
    <group>edr,powershell,code_execution</group>
  </rule>
</group>
```

Configure active response to automatically quarantine suspicious files:

```xml
<!-- /var/ossec/etc/ossec.conf -->
<command>
  <name>quarantine-file</name>
  <executable>quarantine.sh</executable>
  <expect>filename</expect>
</command>

<active-response>
  <command>quarantine-file</command>
  <location>local</location>
  <rules_id>100100</rules_id>
  <timeout>300</timeout>
</active-response>
```

### Key Wazuh Features

- **Vulnerability Detector**: Automatically correlates installed packages against the NVD CVE database. Generates alerts when vulnerable packages are detected on endpoints.
- **FIM (File Integrity Monitoring)**: Monitors critical system files for unauthorized changes. Detects rootkits, webshells, and configuration tampering.
- **SCA (Security Configuration Assessment)**: Runs compliance checks against CIS benchmarks, PCI-DSS, and HIPAA requirements. Generates pass/fail reports per endpoint.
- **Cloud Integration**: Collects logs and security events from AWS CloudTrail, Azure Activity Logs, and GCP Audit Logs for unified visibility.

## Velociraptor: The Forensic Investigation Engine

Velociraptor is a digital forensics and incident response (DFIR) platform that uses a custom query language called VQL (Velociraptor Query Language) to collect and analyze endpoint data. While it shares some DNA with EDR platforms, Velociraptor is fundamentally an investigation tool — it excels at answering "what happened on this endpoint?" rather than continuously monitoring for threats.

Velociraptor's VQL language lets you write queries that look like SQL but operate on endpoint data: process lists, file contents, registry keys, network connections, and memory artifacts. This makes it uniquely powerful for incident investigation — you can query every endpoint for a specific file hash, running process, or network connection in seconds.

### Velociraptor Docker Compose Deployment

Velociraptor provides official Docker images. Deploy the server and have agents connect to it:

```yaml
version: "3.8"

services:
  velociraptor:
    image: velocidex/velociraptor:latest
    container_name: velociraptor
    hostname: velociraptor.example.com
    ports:
      - "8889:8889"
      - "8000:8000"
    volumes:
      - velociraptor-config:/etc/velociraptor
      - velociraptor-data:/var/lib/velociraptor
      - velociraptor-logs:/var/log/velociraptor
    command: >
      velociraptor --config /etc/velociraptor/server.config.yaml frontend -v
    restart: unless-stopped

volumes:
  velociraptor-config:
  velociraptor-data:
  velociraptor-logs:
```

Generate agent configs and deploy to endpoints:

```bash
# Generate server config (first run)
docker exec -it velociraptor \
  velociraptor config generate > server.config.yaml

# Generate agent config for deployment
docker exec -it velociraptor \
  velociraptor --config server.config.yaml \
  config generate > client.config.yaml

# Deploy agent to Linux endpoint
sudo cp client.config.yaml /etc/velociraptor/
sudo velociraptor -c /etc/velociraptor/client.config.yaml client
```

Write a VQL query to detect suspicious process execution:

```yaml
# Custom artifact: Detect PowerShell downloading remote content
name: Custom.EDR.PowerShellDownload
type: CLIENT
parameters:
  - name: LookbackHours
    type: int64
    default: 24

sources:
  - query: |
      SELECT * FROM fork()
      WHERE CommandLine =~ "powershell.*-.(wget|curl|DownloadString|DownloadFile)"
      AND Timestamp > now() - LookbackHours * 3600000000000
```

### Key Velociraptor Features

- **VQL Query Language**: A SQL-like language that queries endpoint artifacts — processes, files, registry, network connections, and memory — in a unified syntax.
- **Hunt Framework**: Deploy queries across thousands of endpoints simultaneously. Results aggregate in the server for analysis.
- **Collection Artifacts**: Pre-built and community-contributed artifacts for common forensic tasks — browser history, scheduled tasks, startup items, and persistence mechanisms.
- **Timeline Analysis**: Reconstruct event timelines from collected artifacts to understand the full scope of an incident.

## Osquery: SQL-Based Endpoint Instrumentation

Osquery treats your operating system as a relational database. Every piece of endpoint data — running processes, loaded kernel modules, network connections, installed packages, and user accounts — is exposed as a SQL table. You write standard SQL queries to investigate and monitor endpoints.

While Osquery itself is a query engine (not a full EDR platform), when combined with a fleet management tool like FleetDM or Kolide, it becomes a powerful EDR solution. The manager distributes queries to agents, collects results, and triggers alerts based on query output.

### Osquery Fleet Docker Compose Deployment

FleetDM provides an open-source fleet management server for Osquery:

```yaml
version: "3.8"

services:
  fleet:
    image: fleetdm/fleet:v4.64.0
    container_name: fleet
    hostname: fleet.example.com
    ports:
      - "8080:8080"
    volumes:
      - fleet-data:/opt/fleet
    environment:
      - FLEET_SERVER_ADDRESS=0.0.0.0:8080
      - FLEET_MYSQL_ADDRESS=mysql:3306
      - FLEET_MYSQL_DATABASE=fleet
      - FLEET_MYSQL_USERNAME=fleet
      - FLEET_MYSQL_PASSWORD=YOUR_SECURE_PASSWORD
      - FLEET_REDIS_ADDRESS=redis:6379
      - FLEET_SERVER_TLS=false
    depends_on:
      - mysql
      - redis
    restart: unless-stopped

  mysql:
    image: docker.io/library/mysql:8.0
    container_name: fleet-mysql
    volumes:
      - fleet-mysql-data:/var/lib/mysql
    environment:
      - MYSQL_DATABASE=fleet
      - MYSQL_USER=fleet
      - MYSQL_PASSWORD=YOUR_SECURE_PASSWORD
      - MYSQL_ROOT_PASSWORD=YOUR_ROOT_PASSWORD
    restart: unless-stopped

  redis:
    image: docker.io/library/redis:7-alpine
    container_name: fleet-redis
    volumes:
      - fleet-redis-data:/data
    restart: unless-stopped

volumes:
  fleet-data:
  fleet-mysql-data:
  fleet-redis-data:
```

Deploy Osquery agents to endpoints using Fleet's enrollment mechanism:

```bash
# Download the Fleet-managed osqueryd package
curl -L https://fleet.example.com/api/latest/osquery-installer.sh | sudo bash

# Or deploy via configuration management (Ansible, Salt):
# /etc/osquery/osquery.conf
{
  "options": {
    "config_plugin": "tls",
    "logger_plugin": "tls",
    "distributed_plugin": "tls",
    "tls_hostname": "fleet.example.com:443",
    "tls_server_certs": "/etc/osquery/fleet.pem"
  },
  "schedule": {
    "pack_running_processes": {
      "query": "SELECT * FROM processes;",
      "interval": 300
    }
  }
}
```

### Key Osquery Features

- **SQL Interface**: Query endpoints using standard SQL. `SELECT name, pid, path FROM processes WHERE name = 'sshd';` returns all SSH daemon processes across managed endpoints.
- **Scheduled Queries**: Run queries on a schedule and ship results to the fleet manager. Alert when query results match threat indicators.
- **Cross-Platform**: Same SQL tables work across Linux, macOS, and Windows. Write once, query everywhere.
- **Pack System**: Group related queries into packs (e.g., "Linux Hardening," "macOS Security," "Windows Persistence") and deploy to relevant endpoint groups.

## Choosing the Right EDR Platform

| Criteria | Choose Wazuh If... | Choose Velociraptor If... | Choose Osquery If... |
|---|---|---|---|
| **Primary use case** | Continuous monitoring + compliance | Incident investigation + forensics | Endpoint visibility + querying |
| **Detection approach** | Rule-based (XML rules) | Query-based (VQL) | Query-based (SQL) |
| **Automated response** | Yes (active response) | Limited (manual VQL actions) | Via Fleet/Orbit scripts |
| **Team expertise** | Security operations / SOC | Digital forensics / IR | DevOps / engineering |
| **Compliance needs** | Built-in (PCI-DSS, HIPAA, NIST) | Custom reports via VQL | Custom reports via SQL |
| **Scale** | 10,000+ endpoints | 5,000+ endpoints | 50,000+ endpoints |
| **Deployment complexity** | Moderate (3-container stack) | Simple (single server) | Moderate (Fleet + MySQL + Redis) |
| **Best for** | SOC teams needing full XDR/SIEM | IR teams responding to incidents | Engineering teams wanting visibility |

## FAQ

### Is a self-hosted EDR platform as effective as a commercial cloud EDR?

For many use cases, yes. Self-hosted platforms like Wazuh provide detection capabilities comparable to commercial EDR — behavioral monitoring, file integrity checking, vulnerability scanning, and automated response. The main trade-off is threat intelligence: commercial vendors share detection signatures across their entire customer base, so a new malware variant detected at one customer is blocked for all others. Self-hosted platforms require you to maintain your own detection rules and threat feeds.

### Can these tools replace my existing antivirus?

Wazuh includes file integrity monitoring and behavioral detection but does not perform real-time antivirus scanning (signature-based file scanning on write). For regulated environments, run Wazuh alongside ClamAV for signature-based scanning. Velociraptor and Osquery are investigation and visibility tools — they complement antivirus but do not replace it.

### How do I write custom detection rules for Wazuh?

Wazuh rules are written in XML and stored in `/var/ossec/etc/rules/local_rules.xml`. Each rule matches decoded log fields using regex patterns and assigns a severity level (1-15). Rules can build on each other — a level-5 rule triggers when a specific log pattern appears, and a level-10 rule triggers when that pattern appears alongside a second indicator. The Wazuh documentation includes hundreds of rule examples.

### Can Velociraptor run detection queries automatically on a schedule?

Yes. Velociraptor supports scheduled hunts through its server configuration. You define a VQL query as an artifact, then configure the server to run that artifact on all (or selected) endpoints at a specified interval. Results are collected and available in the web UI. However, Velociraptor does not have a real-time alerting engine like Wazuh — you need to review hunt results manually or build integrations to forward findings to a SIEM.

### What is the resource overhead of running EDR agents on endpoints?

Wazuh agents typically consume 50-150 MB of RAM and 1-5% CPU on modern hardware, depending on the number of active rules and FIM-monitored paths. Velociraptor agents are lightweight (~30 MB RAM) because they only activate when executing VQL queries. Osquery agents consume 50-200 MB RAM depending on query frequency and result volume. For servers, these overheads are negligible; for resource-constrained IoT or embedded systems, test carefully.

### How do I handle alert fatigue with a self-hosted EDR platform?

Start with a minimal rule set focused on high-confidence detections — known malware hashes, suspicious process trees, and critical vulnerability exploits. Run in detection-only mode for 2-4 weeks to establish a baseline. Then tune rules to suppress expected activity (legitimate admin scripts, backup processes, monitoring tools). Gradually enable automated response for high-confidence rules with low false-positive rates.

## Final Recommendation

For **SOC teams** that need a full-stack security platform with continuous monitoring, compliance reporting, and automated response, Wazuh is the most complete self-hosted EDR solution available. For **incident response teams** that need deep forensic investigation capabilities — answering "what happened on this endpoint?" with precision — Velociraptor's VQL query language is unmatched. For **engineering teams** that want standardized endpoint visibility across Linux, macOS, and Windows using a familiar SQL interface, Osquery with FleetDM provides the cleanest integration path.

Each platform can serve as the foundation of a self-hosted endpoint security program. The choice depends on whether your priority is continuous monitoring (Wazuh), forensic investigation (Velociraptor), or standardized visibility (Osquery).

For related reading, see our [Fleet vs Wazuh vs Teleport endpoint management guide](../2026-04-21-fleet-osquery-vs-wazuh-vs-teleport-self-hosted-endpoint-management-guide-2026/) and [Fail2ban vs SSHGuard vs CrowdSec intrusion prevention guide](../2026-04-24-fail2ban-vs-sshguard-vs-crowdsec-self-hosted-intrusion-prevention-2026/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Wazuh vs Velociraptor vs Osquery: Self-Hosted EDR & Endpoint Security Guide 2026",
  "description": "Compare Wazuh, Velociraptor, and Osquery for self-hosted endpoint detection and response. Complete deployment guide with Docker configs, detection rules, and incident response workflows.",
  "datePublished": "2026-05-02",
  "dateModified": "2026-05-02",
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
