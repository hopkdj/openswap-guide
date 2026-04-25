---
title: "Velociraptor vs GRR vs Osquery: Self-Hosted Threat Hunting & Digital Forensics 2026"
date: 2026-04-25
tags: ["comparison", "guide", "self-hosted", "security", "forensics", "threat-hunting"]
draft: false
description: "Compare Velociraptor, GRR Rapid Response, and Osquery for self-hosted threat hunting, digital forensics, and endpoint visibility. Includes Docker Compose configs, deployment guides, and a decision matrix."
---

When a security incident strikes, the difference between a contained breach and a full compromise comes down to visibility. How fast can you query every endpoint for a suspicious file? Can you pull a memory dump from a compromised server without physical access? Do you have a timeline of what changed before the alert fired?

Self-hosted threat hunting and digital forensics platforms give security teams the ability to investigate endpoints at scale — without shipping sensitive telemetry data to a third-party cloud. In this guide, we compare three open-source frameworks that serve this exact purpose: **Velociraptor** (3,919 stars, actively developed in Go), **GRR Rapid Response** (5,057 stars, maintained by Google in Python), and **Osquery** (23,232 stars, the industry standard for SQL-based endpoint querying).

## Why Self-Hosted Threat Hunting and Forensics Matters

Cloud-based endpoint detection and response (EDR) solutions have grown in popularity, but they come with significant trade-offs for security-conscious organizations:

- **Data sovereignty**: Forensic artifacts — file hashes, registry keys, process trees — contain highly sensitive operational data. Self-hosted platforms keep this data within your infrastructure.
- **Latency during incidents**: When you need to triage 500 servers for a specific indicator of compromise (IOC), waiting for cloud API rate limits is unacceptable. Local infrastructure handles bulk queries faster.
- **Air-gapped environments**: Defense, healthcare, and financial sectors often operate networks that cannot reach the internet. Cloud EDR is simply not an option.
- **Cost at scale**: Per-endpoint pricing models become expensive for organizations with thousands of endpoints. Self-hosted tools use your existing compute resources.
- **Custom artifact development**: Open-source platforms let you write and deploy custom collection artifacts tailored to your environment, without vendor approval cycles.

For teams that need deep endpoint visibility with full control over data retention, access controls, and collection logic, self-hosted threat hunting platforms are the right choice.

## Tool Overview at a Glance

| Feature | Velociraptor | GRR Rapid Response | Osquery |
|---|---|---|---|
| **GitHub Stars** | 3,919 | 5,057 | 23,232 |
| **Language** | Go | Python | C++ |
| **License** | MIT | Apache-2.0 | Apache-2.0 |
| **Last Updated** | April 2026 | April 2026 | April 2026 |
| **Query Language** | VQL (custom DSL) | Python-based flows | SQL |
| **Real-time Response** | Yes (WebSocket) | Yes (HTTP) | No (scheduled/file-based) |
| **Forensic Collection** | Full (memory, disk, artifacts) | Full (disk, memory, registry) | Limited (file system, processes) |
| **Built-in Web UI** | Yes | Yes | No (requires Fleet or Kolide) |
| **Agent Size** | ~30 MB binary | ~100 MB (Python) | ~10 MB binary |
| **Offline Collection** | Yes (local triage mode) | Yes (offline GRR) | Yes (local query) |
| **Hunt/Bulk Queries** | Yes (Hunts) | Yes (Hunts) | No (requires Fleet) |
| **Artifact Repository** | 300+ built-in | ~50 built-in | 300+ tables |
| **Windows Support** | Excellent | Excellent | Excellent |
| **Linux Support** | Excellent | Good | Excellent |
| **macOS Support** | Good | Good | Excellent |

## Velociraptor: Digital Forensics and Incident Response at Scale

Velociraptor, developed by Velocidex, is a purpose-built digital forensics and incident response (DFIR) platform. Its custom query language (VQL) and extensive artifact library make it the most specialized tool for threat hunting among the three.

### Architecture

Velociraptor uses a client-server model with a central server and lightweight agents deployed to endpoints. The server provides a web UI for writing VQL queries, managing hunts, and reviewing collected artifacts. Agents maintain persistent WebSocket connections for real-time interaction.

### Key Strengths

- **300+ pre-built artifacts**: Covering Windows event logs, browser artifacts, prefetch analysis, timeline generation, and more.
- **VQL flexibility**: A purpose-built query language that combines SQL-like syntax with Go templating, enabling complex multi-stage collections.
- **Hunting workflows**: Define hunts that automatically deploy to endpoints matching specific criteria (OS version, hostname pattern, artifact results).
- **Offline triage**: Collect a standalone binary that runs forensic collection on an isolated endpoint and packages results for later analysis.
- **Timeline generation**: Built-in super-timeline creation for forensic analysis across multiple endpoints.

### Docker Compose Deployment

```yaml
services:
  velociraptor:
    image: velocidex/velociraptor:latest
    container_name: velociraptor-server
    restart: unless-stopped
    ports:
      - "8889:8889"   # GUI/API
      - "8000:8000"   # Client comms
    volumes:
      - ./server.config.yaml:/etc/velociraptor/server.config.yaml:ro
      - velociraptor-data:/opt/velociraptor
    environment:
      - VELOX_CONFIG=/etc/velociraptor/server.config.yaml
    networks:
      - velociraptor-net

volumes:
  velociraptor-data:

networks:
  velociraptor-net:
    driver: bridge
```

The server configuration file (`server.config.yaml`) is generated using `velociraptor config generate` and includes frontend settings, SSL certificates, and datastore paths. After generating the config, deploy agents using the generated installer packages for Windows (`.msi`), Linux (`.deb`/`.rpm`), or macOS (`.pkg`).

### Example VQL Query: Find Suspicious PowerShell Execution

```vql
SELECT
    System.TimeCreated.SystemTime AS EventTime,
    System.Computer,
    EventData.CommandLine,
    EventData.ScriptBlockText
FROM winlog(
    channels='Microsoft-Windows-PowerShell/Operational',
    xpath='*[System[(EventID=4104)]]'
)
WHERE
    EventData.CommandLine =~ '(?i)(downloadstring|downloadfile|invoke-expression)'
```

## GRR Rapid Response: Remote Live Forensics

GRR (Google Rapid Response) was created by Google's security team for remote live forensics at scale. It excels at incident response scenarios where you need to quickly triage hundreds of endpoints for specific indicators.

### Architecture

GRR uses a central admin server (GRR Admin) and client agents. The admin server includes a web UI for managing hunts, reviewing results, and scheduling flows. Clients connect back to the server and execute flows — modular units of work for collecting forensic artifacts.

### Key Strengths

- **Battle-tested at Google**: Designed for and used in Google's own incident response workflows.
- **Extensible flow framework**: Write custom flows in Python to collect virtually any forensic artifact.
- **Hunt capability**: Schedule hunts that automatically target endpoints based on client attributes (OS, labels, last seen time).
- **Large file handling**: Efficiently collects and deduplicates large files across many endpoints.
- **Cron jobs**: Schedule recurring collections (e.g., daily process listings, weekly file integrity checks).
- **Offline support**: Offline GRR clients can be run on isolated machines and results uploaded later.

### Docker Compose Deployment

```yaml
services:
  grr-server:
    image: ubuntu/grr-server:latest
    container_name: grr-server
    restart: unless-stopped
    ports:
      - "8000:8000"   # Admin UI
      - "8080:8080"   # Client comms
    volumes:
      - grr-data:/usr/share/grr-server
      - ./grr-server.yaml:/etc/grr/server.local.yaml:ro
    environment:
      - GRR_MONITORING_ENABLE=false
    networks:
      - grr-net

volumes:
  grr-data:

networks:
  grr-net:
    driver: bridge
```

GRR's Docker image includes the full server stack (Admin UI, Worker, Frontend). Deploy client agents using the generated DEB/RPM/EXE packages from the admin UI. The `grr-server.yaml` configuration file controls client communication settings, database backend (SQLite for testing, MySQL for production), and storage paths.

### Example Flow: Collect Suspicious Registry Keys

```python
# Custom GRR flow to search for persistence mechanisms
class RegistryPersistenceFlow(flow_base.FlowBase):
    """Search registry for common persistence locations."""

    args_type = flows.GRRFlowArgs

    def Start(self):
        # Define registry keys to check
        keys = [
            r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
            r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce",
            r"HKEY_CURRENT_USER\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
        ]
        for key in keys:
            self.CallClient("RegistryKey", args=client_pb2.RegistryPath(path=key))

    def End(self):
        self.Log("Registry persistence check complete")
```

## Osquery: SQL-Powered Endpoint Visibility

Osquery, created by Facebook (now Meta), treats the operating system as a relational database. Every aspect of the system — processes, network connections, installed packages, file hashes — is exposed as a SQL table that you can query.

### Architecture

Osquery runs as a daemon (`osqueryd`) on each endpoint, exposing a SQL interface. While osquery itself has no central server, it is typically managed at scale using **Fleet Device Management** (open-source) or Kolide (commercial). The Fleet server provides a web UI, distributed query management, and result collection.

### Key Strengths

- **23,000+ GitHub stars**: The most popular endpoint visibility tool in the open-source ecosystem.
- **SQL query language**: Familiar syntax that any analyst can learn. `SELECT * FROM processes WHERE name = 'sshd'` just works.
- **300+ tables**: Covering processes, network connections, file integrity, kernel modules, scheduled tasks, browser data, and more.
- **Scheduled queries**: Run queries on a cron-like schedule and collect results for trending and alerting.
- **Pack system**: Group related queries into "packs" (e.g., incident response pack, CIS benchmark pack).
- **Cross-platform parity**: Consistent table schemas across Windows, Linux, and macOS.

### Docker Compose Deployment (Fleet + Osquery)

Since osquery requires a management layer for fleet-scale operations, here is a deployment using Fleet (the open-source osquery manager):

```yaml
services:
  fleet-server:
    image: fleetdm/fleet:latest
    container_name: fleet-server
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - fleet-data:/opt/fleet
    environment:
      - FLEET_SERVER_ADDRESS=0.0.0.0:8080
      - FLEET_MYSQL_ADDRESS=mysql:3306
      - FLEET_MYSQL_DATABASE=fleet
      - FLEET_MYSQL_USERNAME=fleet
      - FLEET_MYSQL_PASSWORD=fleet_password
      - FLEET_REDIS_ADDRESS=redis:6379
      - FLEET_SERVER_TLS=false
    depends_on:
      - mysql
      - redis
    networks:
      - fleet-net

  mysql:
    image: mysql:8.0
    container_name: fleet-mysql
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD=root_password
      - MYSQL_DATABASE=fleet
      - MYSQL_USER=fleet
      - MYSQL_PASSWORD=fleet_password
    volumes:
      - mysql-data:/var/lib/mysql
    networks:
      - fleet-net

  redis:
    image: redis:7-alpine
    container_name: fleet-redis
    restart: unless-stopped
    networks:
      - fleet-net

volumes:
  fleet-data:
  mysql-data:

networks:
  fleet-net:
    driver: bridge
```

Deploy osquery agents using the Fleet enrollment secret. Agents connect to the Fleet server and receive scheduled queries, configuration profiles, and live query requests.

### Example Osquery Query: Detect Suspicious Network Connections

```sql
SELECT
    p.name AS process_name,
    p.pid,
    p.path AS process_path,
    s.local_address,
    s.local_port,
    s.remote_address,
    s.remote_port,
    s.state
FROM process_open_sockets s
JOIN processes p ON s.pid = p.pid
WHERE s.remote_port IN (4444, 5555, 8888, 1337, 31337)
    AND s.state = 'ESTABLISHED';
```

## Decision Matrix: Which Tool Should You Choose?

| Scenario | Recommended Tool | Why |
|---|---|---|
| **Incident response on Windows endpoints** | Velociraptor | Best artifact library for Windows forensics (prefetch, USN journal, event logs) |
| **Large-scale endpoint visibility** | Osquery + Fleet | SQL is easiest to train analysts on; 300+ tables cover most use cases |
| **Remote live forensics at Google scale** | GRR | Proven at massive scale; Python flows are highly extensible |
| **Memory forensics** | Velociraptor | Built-in memory acquisition and analysis capabilities |
| **Cross-platform compliance monitoring** | Osquery | Consistent table schemas across Windows, Linux, macOS |
| **Offline/air-gapped endpoint triage** | Velociraptor | Standalone triage binary works without server connectivity |
| **Recurring forensic collections** | GRR | Cron jobs and scheduled hunts for ongoing monitoring |
| **Smallest agent footprint** | Osquery | ~10 MB binary vs 30 MB (Velociraptor) vs 100 MB (GRR) |

## Deployment Comparison

| Aspect | Velociraptor | GRR | Osquery + Fleet |
|---|---|---|---|
| **Docker Setup Complexity** | Low (single container) | Medium (server + optional workers) | High (server + MySQL + Redis) |
| **Database Requirement** | SQLite/BadgerDB (built-in) | MySQL/PostgreSQL (required for prod) | MySQL + Redis (required) |
| **Agent Deployment** | MSI/DEB/RPM packages | DEB/RPM/EXE packages | DEB/RPM/PKG/MSI via Fleet |
| **SSL/TLS Setup** | Auto-generated certs | Manual config | Fleet handles TLS |
| **Horizontal Scaling** | Frontend pool + MinIO storage | Multiple workers + datastore | Fleet load balancer + MySQL cluster |
| **Minimum Resources** | 2 CPU, 4 GB RAM | 4 CPU, 8 GB RAM | 4 CPU, 8 GB RAM (plus DB) |

## Related Guides

For a comprehensive security monitoring stack, consider combining threat hunting tools with complementary systems:

- Our [Suricata vs Snort vs Zeek IDS/IPS guide](../suricata-vs-snort-vs-zeek-self-hosted-ids-ips-guide-2026/) covers network-level detection to complement endpoint visibility.
- The [fleet osquery vs Wazuh vs Teleport endpoint management guide](../fleet-osquery-vs-wazuh-vs-teleport-self-hosted-endpoint-management-guide-2026/) explores broader endpoint management beyond forensics.
- For centralized security event correlation, see our [self-hosted SIEM comparison](../self-hosted-siem-wazuh-security-onion-elastic-guide/) covering Wazuh, Security Onion, and the Elastic Stack.
- The [Falco vs Osquery vs Auditd runtime security guide](../falco-vs-osquery-vs-auditd-self-hosted-runtime-security-guide/) provides a deep dive into real-time kernel-level monitoring that pairs well with periodic threat hunting.

## FAQ

### What is the difference between threat hunting and endpoint detection?

Endpoint detection (EDR) monitors for known malicious patterns and raises alerts automatically. Threat hunting is a proactive process where analysts actively search for indicators of compromise (IOCs) and anomalous behavior that may have evaded automated detection. Tools like Velociraptor, GRR, and Osquery empower analysts to write custom queries and investigate hypotheses across all endpoints.

### Can these tools replace a commercial EDR solution?

Not entirely. Commercial EDR platforms offer features like behavioral analysis, machine learning-based detection, and automated response actions that open-source tools do not provide. However, Velociraptor, GRR, and Osquery excel at deep forensic collection and ad-hoc investigation — capabilities that complement EDR by providing the detailed evidence needed after an alert fires.

### Do these tools work in air-gapped (offline) environments?

Yes. All three tools support fully offline deployments. Velociraptor has a standalone triage mode that runs forensic collection without any server connectivity. GRR offers offline clients that can be executed on isolated machines with results uploaded later. Osquery runs locally on each endpoint and can write results to local files that are periodically collected.

### Which tool has the easiest learning curve?

Osquery has the lowest barrier to entry because it uses standard SQL. Anyone familiar with `SELECT`, `WHERE`, and `JOIN` can start writing queries immediately. Velociraptor's VQL is more powerful but requires learning a domain-specific language. GRR's Python-based flows offer the most flexibility but require Python programming knowledge.

### How many endpoints can each tool handle?

Osquery + Fleet has been deployed at organizations with 100,000+ endpoints. Velociraptor handles tens of thousands of concurrent connections with proper server sizing. GRR was designed at Google for massive scale and can handle hundreds of thousands of clients when properly configured with distributed workers and a production database backend.

### Can I run multiple tools together?

Absolutely. A common pattern is using Osquery + Fleet for broad endpoint visibility and scheduled queries, then deploying Velociraptor on a subset of critical servers for deep forensic investigation when an Osquery query returns suspicious results. GRR can serve as a tertiary tool for specialized collection tasks not covered by the other two.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Velociraptor vs GRR vs Osquery: Self-Hosted Threat Hunting & Digital Forensics 2026",
  "description": "Compare Velociraptor, GRR Rapid Response, and Osquery for self-hosted threat hunting, digital forensics, and endpoint visibility. Includes Docker Compose configs, deployment guides, and a decision matrix.",
  "datePublished": "2026-04-25",
  "dateModified": "2026-04-25",
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
