---
title: "Self-Hosted SIEM Guide: Wazuh vs Security Onion vs Elastic Security 2026"
date: 2026-04-13
tags: ["comparison", "guide", "self-hosted", "security", "monitoring"]
draft: false
description: "Complete guide to open-source SIEM solutions in 2026. Compare Wazuh, Security Onion, and Elastic Security for self-hosted threat detection and log management."
---

Security Information and Event Management (SIEM) platforms sit at the center of any serious security operation. They collect logs from every system on your network, correlate events to detect threats, and provide the forensic data you need when something goes wrong. Commercial SIEM solutions from vendors like Splunk, IBM QRadar, and Datadog can cost tens of thousands of dollars per year — pricing that simply doesn't work for small teams, homelabs, or budget-conscious organizations.

The open-source SIEM ecosystem has matured dramatically. In 2026, self-hosted solutions offer enterprise-grade threat detection, real-time alerting, compliance reporting, and deep log analysis without the licensing fees. This guide compares the three leading open-source SIEM platforms: Wazuh, Security Onion, and Elastic Security.

## Why Self-Host Your SIEM?

Running your own SIEM gives you capabilities that hosted services can't match:

**Complete data ownership.** Every log, every alert, every piece of forensic evidence stays on your infrastructure. There's no third-party vendor with access to your security telemetry, and no risk of a SaaS provider going offline or changing their data retention policies.

**Unlimited log retention.** Commercial SIEM providers charge by data volume — ingest more logs and your bill explodes. Self-hosted, you're only limited by your storage. Keep years of logs for compliance, forensic investigations, or historical trend analysis at marginal cost.

**Full customization.** Build detection rules that match your exact environment. Integrate with internal tools, custom applications, and proprietary protocols. Most commercial SIEMs restrict what you can modify; open-source platforms let you change everything.

**Cost predictability.** Once your infrastructure is sized correctly, the ongoing cost is hardware and maintenance — not per-gigabyte ingest fees. For organizations generating 100GB+ of logs daily, the savings are enormous.

**Regulatory compliance.** Many compliance frameworks (GDPR, HIPAA, PCI DSS, SOC 2) require strict control over where log data is stored and who can access it. Self-hosting eliminates the compliance questions that come with sending security data to external vendors.

## Wazuh: The Comprehensive Open-Source SIEM

Wazuh is the most feature-complete open-source SIEM available. Originally a fork of OSSEC, it has evolved into a full-featured platform combining SIEM, endpoint detection and response (EDR), vulnerability detection, and compliance monitoring. It's used by thousands of organizations worldwide and maintains an active development community backed by Wazuh Inc.

Wazuh's architecture centers on three components: the Wazuh agent (installed on endpoints), the Wazuh server (log processing and analysis), and a visualization layer powered by OpenSearch Dashboards. The platform supports agentless monitoring via syslog for network devices, cloud services, and any system that can forward logs.

### Key Features

- **Endpoint security monitoring.** File integrity monitoring, rootkit detection, and process auditing across Linux, Windows, macOS, and AIX systems.
- **Vulnerability detection.** Scans installed packages against CVE databases (NVD, Red Hat, Debian, Canonical, Arch) and generates vulnerability reports without requiring network vulnerability scans.
- **Regulatory compliance mapping.** Built-in mapping for PCI DSS, HIPAA, NIST 800-53, GDPR, and CIS benchmarks. Each alert is tagged with the relevant compliance requirement.
- **Cloud security monitoring.** Native integrations with AWS (CloudTrail, S3, VPC Flow Logs, GuardDuty), Azure (Activity Logs, Defender for Cloud), and Google Cloud (Audit Logs, Security Command Center).
- **Active response.** Automated incident response — block IPs via firewall rules, restart services, isolate compromised hosts, or execute custom scripts when threats are detected.
- **Log analysis engine.** Decoders and rules written in XML for parsing structured and unstructured log formats. Over 1,500 built-in rules covering common attack patterns.

### Wazuh Installation Guide

The fastest way to get Wazuh running is via the all-in-one deployment script, which installs the server, indexer, and dashboard on a single host. For production use, Wazuh recommends separating the indexer and dashboard components.

```bash
# Download and run the all-in-one installer
curl -sO https://packages.wazuh.com/5.0/wazuh-install.sh
sudo bash ./wazuh-install.sh -a

# The installer will output:
# - Wazuh dashboard URL (https://<your-server-ip>)
# - Admin username and password
# - Enrollment command for agents
```

For a [docker](https://www.docker.com/)-based deployment, which is ideal for testing and isolated environments:

```yaml
# docker-compose-wazuh.yml
services:
  wazuh.manager:
    image: wazuh/wazuh-manager:5.0.0
    hostname: wazuh.manager
    ports:
      - "1514:1514"    # Agent communication
      - "1515:1515"    # Agent enrollment
      - "514:514/udp"  # Syslog reception
      - "55000:55000"  # REST API
    environment:
      - INDEXER_URL=https://wazuh.indexer
      - INDEXER_USERNAME=admin
      - INDEXER_PASSWORD=SecretPassword
    volumes:
      - wazuh_api_configuration:/var/ossec/api/configuration
      - wazuh_etc:/var/ossec/etc
      - wazuh_logs:/var/ossec/logs
      - wazuh_queue:/var/ossec/queue
      - wazuh_var_multigroups:/var/ossec/var/multigroups
      - wazuh_integrations:/var/ossec/integrations
      - wazuh_active_response:/var/ossec/active-response/bin
      - wazuh_agentless:/var/ossec/agentless
      - wazuh_wodles:/var/ossec/wodles
      - filebeat_etc:/etc/filebeat
      - filebeat_var:/var/lib/filebeat

  wazuh.indexer:
    image: wazuh/wazuh-indexer:5.0.0
    hostname: wazuh.indexer
    ports:
      - "9200:9200"
    environment:
      - OPENSEARCH_JAVA_OPTS=-Xms1g -Xmx1g
    volumes:
      - wazuh-indexer-data:/var/lib/wazuh-indexer

  wazuh.dashboard:
    image: wazuh/wazuh-dashboard:5.0.0
    hostname: wazuh.dashboard
    ports:
      - "443:443"
    environment:
      - INDEXER_URL=https://wazuh.indexer:9200
      - INDEXER_USERNAME=admin
      - INDEXER_PASSWORD=SecretPassword
    depends_on:
      - wazuh.indexer
    links:
      - wazuh.indexer:wazuh.indexer

volumes:
  wazuh_api_configuration:
  wazuh_etc:
  wazuh_logs:
  wazuh_queue:
  wazuh_var_multigroups:
  wazuh_integrations:
  wazuh_active_response:
  wazuh_agentless:
  wazuh_wodles:
  filebeat_etc:
  filebeat_var:
  wazuh-indexer-data:
```

```bash
# Deploy with Docker Compose
docker compose -f docker-compose-wazuh.yml up -d

# Wait for services to initialize (about 2-3 minutes)
# Access the dashboard at https://<your-server-ip>:443
```

Deploying a Wazuh agent on an endpoint is straightforward:

```bash
# Linux agent installation
curl -sO https://packages.wazuh.com/5.0/wazuh-agent.deb
sudo WAZUH_MANAGER="10.0.0.5" dpkg -i ./wazuh-agent.deb
sudo systemctl enable wazuh-agent
sudo systemctl start wazuh-agent

# Windows agent (PowerShell)
Invoke-WebRequest -Uri https://packages.wazuh.com/5.0/wazuh-agent-5.0.0-1.msi -OutFile wazuh-agent.msi
.\wazuh-agent.msi /q WAZUH_MANAGER="10.0.0.5"

# macOS agent
curl -sO https://packages.wazuh.com/5.0/wazuh-agent-5.0.0-1.pkg
sudo installer -pkg ./wazuh-agent-5.0.0-1.pkg -target /
```

### Custom Detection Rules

Wazuh rules are defined in XML and can be customized for your specific environment. Here's an example of a custom rule to detect SSH brute-force attacks with a lower threshold than the default:

```xml
<!-- /var/ossec/etc/rules/local_rules.xml -->
<group name="syslog,sshd,">
  <rule id="100001" level="5">
    <if_sid>5716</if_sid>
    <srcip>!</srcip>
    <description>SSH authentication failure.</description>
    <group>authentication_failed,</group>
  </rule>

  <rule id="100002" level="10" frequency="5" timeframe="120">
    <if_matched_sid>100001</if_matched_sid>
    <same_source_ip/>
    <description>SSH brute force attack detected: 5 attempts in 2 minutes.</description>
    <group>brute_force,pci_dss_11.4,gdpr_IV_35.7.d,</group>
  </rule>
</group>
```

After adding custom rules, restart the manager:

```bash
sudo systemctl restart wazuh-manager
```

## Security Onion: The Network Security Specialist

Security Onion is a Linux distribution purpose-built for threat hunting, network security monitoring, and log management. Unlike Wazuh's endpoint-first approach, Security Onion focuses on network-level visibility — capturing and analyzing network traffic, extracting files from packet captures, and correlating network events with endpoint data.

The platform bundles a curated collection of open-source security tools into a unified deployment: Suricata for network intrusion detection, Zeek for network protocol analysis, Strelka for file extraction and analysis, and CyberChef for data transformation. The management interface (Security Onion Console) provides centralized configuration and monitoring across all components.

### Key Features

- **Full packet capture.** Optionally capture and store raw network traffic for deep forensic analysis. Replay PCAP files to investigate incidents with complete network context.
- **Network intrusion detection.** Suricata provides signature-based and anomaly-based detection of network threats with automatic rule updates from Emerging Threats and other threat intelligence feeds.
- **Protocol analysis.** Zeek generates structured logs for every network protocol — HTTP, DNS, SMTP, SSH, TLS, SMB, and dozens more — creating a searchable record of all network activity.
- **File extraction and analysis.** Strelka extracts files from network traffic, email attachments, and archives, then analyzes them for malware indicators. Integration with YARA rules and ClamAV signatures.
- **Hunt framework.** Dedicated investigation interface for threat hunting with pivot-based exploration, timeline reconstruction, and saved hunt queries for repeatable investigations.
- **Playbook-driven response.** Guided investigation playbooks that walk analysts through common threat scenarios, ensuring consistent response procedures.

### Security Onion Installation Guide

Security Onion provides an ISO-based installer that handles the complete deployment. The recommended minimum specification is 8 CPU cores, 24GB RAM, and 100GB storage for the evaluation profile. Production deployments typically need 16+ cores and 64GB+ RAM.

```bash
# Download the ISO
# Visit https://securityonionsolutions.com/software/
# Download securityonion-2.4.x.iso

# Boot from ISO on dedicated hardware or VM
# The installer will guide you through:
# 1. Network interface selection (management vs. monitoring)
# 2. Deployment profile (standalone, distributed, or eval)
# 3. Storage configuration
# 4. Component selection (which tools to enable)

# For a quick evaluation deployment, select "eval" profile.
# This deploys everything on a single node with minimal resource usage.
```

After installation, access the Security Onion Console:

```bash
# The console is available at:
# https://<your-server-ip>

# Initial setup creates the admin user and configures
# network monitoring interfaces, threat intel feeds,
# and alert routing.

# Add monitoring interfaces:
sudo so-allow
# Select the network interfaces to monitor for traffic

# Enable community threat intel feeds:
# Navigate to Config > Threat Intel in the console
# Enable Emerging Threats, Abuse.ch, and MISP feeds
```

### Configuring Suricata Rules

Security Onion's Suricata instance can be customized with community and private rules:

```yaml
# /opt[minio](https://min.io/)altstack/local/pillar/minions/<sensor-hostname>.sls
# Add a custom Suricata rules file

suricata:
  rules:
    custom_rules:
      - alert http $EXTERNAL_NET any -> $HOME_NET any (
          msg:"ET TROJAN Possible Ransomware C2 Communication";
          flow:established,to_client;
          content:"Content-Type";
          content:"application/octet-stream";
          threshold: type limit, track by_src, count 1, seconds 300;
          classtype:trojan-activity;
          sid:1000001;
          rev:1;
        )
```

After updating rules, deploy the changes:

```bash
# Deploy new Suricata configuration
sudo salt-call state.apply suricata

# Verify rules are loaded
sudo grep -c "1000001" /opt/so/rules/nids/all.rules
```

### Querying Network Logs with Socat

Security Onion stores all logs in Elasticsearch. Here are common investigation queries using the Kibana dev tools or the `so-elastalert` API:

```bash
# Search for DNS queries to suspicious domains
# In Kibana Discover or via curl:
curl -k -X POST "https://localhost:9200/so-zeek-*/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "wildcard": {
        "zeek.dns.query": "*.suspicious-domain.tld"
      }
    },
    "size": 100,
    "_source": ["@timestamp", "zeek.dns.query", "zeek.dns.answers", "source.ip"]
  }'

# Find large file transfers via HTTP
curl -k -X POST "https://localhost:9200/so-zeek-*/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "range": {
        "zeek.http.resp_body_bytes": { "gte": 10000000 }
      }
    },
    "size": 50
  }'
```

## Elastic Security: The Enterprise-Grade Platform

Elastic Security (part of the Elastic Stack, formerly ELK) provides a SIEM and endpoint security platform built on the same engine that powers the world's most popular log management stack. It combines log ingestion, search, alerting, threat hunting, and endpoint protection in a single platform that scales from a single laptop to planet-sized deployments.

The platform uses Elastic Agents — a unified agent that combines the functionality of Beats, Filebeat, Metricbeat, and endpoint protection — deployed via Fleet, a centralized management interface. This simplifies deployment and management compared to running multiple agents on each endpoint.

### Key Features

- **Unified log management and SIEM.** Ingest logs from any source — applications, infrastructure, network devices, cloud services — and correlate them with security alerts in a single search interface.
- **Elastic Agent and Fleet.** Single agent deployment managed centrally. Fleet handles version upgrades, policy distribution, and agent health monitoring across thousands of endpoints.
- **Prebuilt detection rules.** Over 500 prebuilt detection rules covering MITRE ATT&CK techniques, with automatic rule updates delivered through the Elastic package registry.
- **Threat intelligence integration.** Import threat intel feeds in STIX/TAXII format. Elastic automatically enriches events with threat intel indicators and generates alerts on matches.
- **Timeline and case management.** Built-in investigation timeline for reconstructing attack chains. Case management for tracking incidents, assigning analysts, and documenting response actions.
- **Machine learning anomaly detection.** Unsupervised machine learning models detect anomalous behavior patterns — unusual login times, rare process execution, abnormal network traffic volumes — without requiring hand-tuned rules.
- **Endpoint security.** Full endpoint protection including malware prevention, ransomware behavior detection, and application allowlisting (available in Elastic Security's full-featured tiers).

### Elastic Security Installation Guide

The quickest way to deploy Elastic Security for evaluation is via Docker Compose. For prod[kubernetes](https://kubernetes.io/)astic recommends Kubernetes or their Elastic Cloud hosted offering.

```yaml
# docker-compose-elastic.yml
version: "3.8"
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.17.0
    container_name: elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=true
      - xpack.security.enrollment.enabled=true
      - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
      - ELASTIC_PASSWORD=YourStrongPassword123!
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data
    networks:
      - elastic-net

  kibana:
    image: docker.elastic.co/kibana/kibana:8.17.0
    container_name: kibana
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=https://elasticsearch:9200
      - ELASTICSEARCH_USERNAME=kibana_system
      - ELASTICSEARCH_PASSWORD=YourStrongPassword123!
    depends_on:
      - elasticsearch
    networks:
      - elastic-net

volumes:
  elasticsearch-data:
    driver: local

networks:
  elastic-net:
    driver: bridge
```

```bash
# Start the stack
docker compose -f docker-compose-elastic.yml up -d

# Wait for Elasticsearch to be ready (30-60 seconds)
curl -k -u elastic:YourStrongPassword123! https://localhost:9200

# Access Kibana at http://<your-server-ip>:5601
# Log in with elastic / YourStrongPassword123!
# Navigate to Security to activate the SIEM module
```

### Configuring Elastic Agents

Once Kibana is running, set up Fleet to manage Elastic Agents across your infrastructure:

```bash
# In Kibana: Management > Fleet > Settings
# Configure the Fleet Server URL

# Generate an enrollment token:
# Fleet > Agent Policies > Create agent policy
# Name it "security-endpoints" and enable:
#   - Endpoint Security
#   - System integration (logs and metrics)
#   - Auditd Manager (Linux systems)

# Install Elastic Agent on a Linux endpoint:
curl -L -O https://artifacts.elastic.co/downloads/beats/elastic-agent/elastic-agent-8.17.0-linux-x86_64.tar.gz
tar xzvf elastic-agent-8.17.0-linux-x86_64.tar.gz
cd elastic-agent-8.17.0-linux-x86_64

sudo ./elastic-agent install \
  --url=https://<fleet-server-ip>:8220 \
  --enrollment-token=<YOUR_ENROLLMENT_TOKEN> \
  --insecure

# Install on Windows:
# Download the .zip from the same URL, extract, and run:
# .\elastic-agent.exe install --url=https://<fleet-server-ip>:8220 --enrollment-token=<TOKEN>
```

### Creating Custom Detection Rules

Elastic Security supports multiple rule types — query-based, machine learning, threshold, and EQL (Event Query Language). Here's an EQL rule to detect a common lateral movement pattern:

```json
// Create via Kibana Security > Rules > Create rule > EQL
{
  "name": "Suspicious Remote Execution via PsExec",
  "description": "Detects PsExec-style remote service creation",
  "language": "eql",
  "query": """
    sequence by host.id with maxspan=10s
    [process where event.type == "start" and process.name == "sc.exe" and
     process.args == "create" and process.args : ("\\\\*", "binPath=")]
    [process where event.type == "start" and process.name == "sc.exe" and
     process.args == "start"]
  """,
  "index": ["logs-endpoint.events.process-*", "winlogbeat-*"],
  "severity": "high",
  "risk_score": 73,
  "tags": ["MITRE ATT&CK T1021.002", "lateral-movement"],
  "rule_id": "custom-psexec-detection",
  "threat": [
    {
      "framework": "MITRE ATT&CK",
      "technique": [{ "id": "T1021.002", "name": "SMB/Windows Admin Shares" }]
    }
  ]
}
```

## Feature Comparison

| Feature | Wazuh | Security Onion | Elastic Security |
|---------|-------|----------------|------------------|
| **Primary focus** | Endpoint security & compliance | Network security monitoring | Unified log management & SIEM |
| **Endpoint agent** | Wazuh Agent (lightweight, 30-50MB RAM) | None required (network-centric) | Elastic Agent (comprehensive, 100-200MB RAM) |
| **Network traffic analysis** | Limited (via Suricata integration) | Full packet capture + Zeek + Suricata | Via Fleet integrations (Packetbeat) |
| **Vulnerability scanning** | Built-in CVE scanner | Via Nipper/external tools | Via third-party integrations |
| **Compliance reporting** | PCI DSS, HIPAA, NIST, GDPR, CIS | Custom | Custom dashboards |
| **Active response** | Built-in (firewall, scripts, custom) | Via Playbooks | Via Connectors and SOAR integrations |
| **Machine learning** | Limited | Via external integrations | Built-in anomaly detection |
| **Threat intelligence** | MITRE ATT&CK mapping | MISP, Emerging Threats, Abuse.ch | STIX/TAXII, MISP, commercial feeds |
| **Cloud monitoring** | AWS, Azure, GCP native | Via Zeek integrations | AWS, Azure, GCP native |
| **Scalability** | Up to 100K+ endpoints | Up to 50K EPS (distributed) | Planet-scale (Elastic Cloud proven) |
| **Minimum resources** | 4 CPU, 8GB RAM (all-in-one) | 8 CPU, 24GB RAM (eval profile) | 4 CPU, 8GB RAM (single node) |
| **Learning curve** | Moderate | Steep | Moderate to steep |
| **Community** | Very active (20K+ GitHub stars) | Active (dedicated community) | Massive (entire Elastic ecosystem) |
| **License** | GPL 2.0 + Apache 2.0 | GPLv3 + Apache 2.0 | SSPL (free for self-hosted use) |
| **Commercial support** | Wazuh Inc. | Security Onion Solutions | Elastic N.V. |

## Choosing the Right SIEM for Your Environment

The best choice depends on your specific use case:

**Choose Wazuh if** you need endpoint-focused security with built-in compliance reporting. It's the strongest option for organizations that must demonstrate compliance with PCI DSS, HIPAA, or NIST frameworks. The vulnerability detection engine alone justifies the deployment for many teams. Wazuh also has the gentlest learning curve of the three options.

**Choose Security Onion if** network visibility is your primary concern. It's the only platform that provides full packet capture and deep protocol analysis out of the box. Ideal for SOC teams that need to investigate network-level incidents, extract files from traffic, and hunt for threats that endpoint agents might miss. The steep learning curve is offset by unmatched network forensics capabilities.

**Choose Elastic Security if** you already run the Elastic Stack or need a platform that unifies log management, observability, and security in a single deployment. It's the most scalable option and has the richest integration ecosystem. The machine learning anomaly detection catches threats that rule-based systems miss, making it valuable for mature security operations.

## Production Deployment Best Practices

Regardless of which platform you choose, follow these guidelines for production deployments:

```bash
# 1. Separate components across dedicated servers
# Never run indexer/search/manager on the same node in production.
# Minimum production topology:
#   - 3x Indexer/Elasticsearch nodes (for high availability)
#   - 1-2 Manager/processing nodes
#   - 1 Dashboard/Kibana node
#   - 1 Fleet/log ingestion node (per 10K endpoints)

# 2. Size your storage correctly
# Estimate daily log volume and retention requirements:
# Daily storage (GB) = endpoints × avg_logs_per_day × avg_log_size_KB / 1024
# Total storage = Daily storage × retention_days × 1.2 (20% overhead)

# 3. Secure the SIEM infrastructure itself
# The SIEM is a high-value target. Hardening is critical:
ufw allow from <management_network>/24 to any port 443
ufw allow from <agent_network>/16 to any port 1514
ufw default deny
# Enable TLS for all internal communications
# Use mutual TLS for agent enrollment
# Rotate certificates quarterly

# 4. Configure log source validation
# Ensure every log source has a corresponding parsing rule
# Set up alerts for log source failures (agent offline, syslog not received)
# Monitor log volume anomalies — sudden drops indicate collection failures

# 5. Back up your configuration and detection rules
# Rules, decoders, and custom configurations must be version-controlled
# Back up the indexer daily with snapshot/restore
# Store backups on separate infrastructure from the SIEM

# 6. Test your detection rules regularly
# Use atomic red team techniques or custom attack simulation
# Verify that every critical detection rule fires as expected
# Document false positive rates and tune thresholds accordingly
```

The open-source SIEM landscape in 2026 offers genuine enterprise capability without enterprise pricing. Whether you choose Wazuh for endpoint-centric security, Security Onion for network forensics, or Elastic Security for unified observability and security, you can build a world-class detection capability on commodity hardware. The key is starting with a clear understanding of your threat model, sizing your infrastructure correctly, and committing to ongoing rule tuning and operational maturity.

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
