---
title: "Fleet vs Wazuh vs Teleport: Self-Hosted Endpoint Management & Device Compliance Guide 2026"
date: 2026-04-21
tags: ["comparison", "guide", "self-hosted", "security", "endpoint-management", "compliance"]
draft: false
description: "Compare Fleet, Wazuh, and Teleport for self-hosted endpoint management, device compliance monitoring, and infrastructure access control. Complete Docker deployment guides with real configuration examples."
---

Managing hundreds or thousands of endpoints — servers, workstations, laptops, and containers — is one of the most com[plex](https://www.plex.tv/) operational challenges for infrastructure teams. Commercial endpoint management platforms like Jamf, CrowdStrike Falcon, and Tanium charge per-device licensing fees that scale into tens of thousands of dollars annually. They also require your telemetry data to flow through third-party cloud infrastructure.

In 2026, three open-source projects have emerged as production-ready alternatives for self-hosted endpoint management: **Fleet** (built on osquery), **Wazuh** (unified XDR/SIEM), and **Teleport** (infrastructure access with device trust). Each takes a fundamentally different approach to the problem, and the right choice depends on whether your priority is visibility, security, or access control.

This guide compares all three [docker](https://www.docker.com/)rms with hands-on Docker deployment instructions, so you can evaluate them on your own infrastructure.

## Why Self-Host Endpoint Management

The case for self-hosting endpoint management goes beyond cost savings:

**Complete data sovereignty.** Endpoint telemetry includes software inventory, user activity, network connections, and system configuration. When you self-host, this sensitive data never leaves your network. You control retention, encryption, and access — no vendor audits or data residency concerns.

**Unlimited device coverage.** Commercial platforms charge per enrolled device. Fleet's open-source tier, Wazuh, and Teleport Community Edition have no device limits. Monitor ten endpoints or ten thousand — the only constraint is your server capacity.

**Custom compliance frameworks.** Regulatory requirements vary by industry and region. Self-hosted tools let you define custom compliance queries, audit policies, and reporting schedules that map directly to your specific obligations — SOC 2, HIPAA, PCI DSS, or internal security standards.

**Deep infrastructure integration.** Self-hosted endpoint managers expose raw APIs, webhook endpoints, and direct database access. You can pipe telemetry into your existing SIEM, trigger automated remediation through your orchestration platform, or feed compliance data into your internal dashboards.

**Air-gapped and isolated environments.** Defense contractors, healthcare facilities, and financial institutions often operate in network-segmented environments. Self-hosted endpoint management tools can run entirely within isolated networks with no external connectivity.

## Fleet — osquery-Powered Device Visibility

Fleet ([fleetdm/fleet](https://github.com/fleetdm/fleet), 6,261 stars) is the leading open-source osquery management platform. Built by the team behind Kolide, Fleet provides a web UI for querying, monitoring, and managing endpoints at scale using osquery's SQL-powered operating system instrumentation.

### Key Capabilities

- **Live SQL queries** across all enrolled endpoints — ask questions like "which machines have SSH port 22 open?" or "what version of OpenSSL is running?"
- **Automated policy checks** — define compliance rules as SQL queries and get real-time pass/fail status per device
- **Software inventory** — automatic detection of installed packages, browser extensions, and running services
- **MDM enrollment** — Apple MDM support for device enrollment, configuration profiles, and software distribution
- **Vulnerability detection** — correlates installed software versions against known CVE databases
- **GitOps workflows** — manage queries, policies, and labels as version-controlled YAML files

### Architecture

Fleet requires MySQL (or MariaDB) for its database and Redis for caching. The Fleet server acts as the central control plane, and osquery agents on each endpoint connect back to it via TLS.

### Docker Deployment

```yaml
# docker-compose.fleet.yml
services:
  mysql:
    image: mysql:8.0
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: fleet_root_pass
      MYSQL_DATABASE: fleet
      MYSQL_USER: fleet
      MYSQL_PASSWORD: fleet_secret
    volumes:
      - fleet_mysql:/var/lib/mysql
    command:
      - --max_allowed_packet=536870912

  redis:
    image: redis:7-alpine
    restart: always

  fleet:
    image: fleetdm/fleet:latest
    restart: always
    ports:
      - "8080:8080"
    depends_on:
      - mysql
      - redis
    environment:
      FLEET_MYSQL_ADDRESS: mysql:3306
      FLEET_MYSQL_DATABASE: fleet
      FLEET_MYSQL_USERNAME: fleet
      FLEET_MYSQL_PASSWORD: fleet_secret
      FLEET_REDIS_ADDRESS: redis:6379
      FLEET_SERVER_TLS: "false"
      FLEET_SERVER_ADDRESS: "0.0.0.0:8080"
    command:
      - fleet
      - serve

volumes:
  fleet_mysql:
```

Start the stack:

```bash
docker compose -f docker-compose.fleet.yml up -d
```

Access the Fleet UI at `http://localhost:8080`. The first-run wizard will guide you through initial setup, including creating an admin account and generating the osquery enrollment secret.

### Enrolling an Endpoint

On each target machine, install osquery and point it at your Fleet server:

```bash
# Install osquery (Ubuntu/Debian)
export OSQUERY_KEY=1484120AC4E9F8A1A577AEEE97A80C63C9D8B80B
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys $OSQUERY_KEY
sudo add-apt-repository 'deb [arch=amd64] https://pkg.osquery.io/deb deb main'
sudo apt-get update && sudo apt-get install -y osquery

# Configure osquery to connect to Fleet
sudo osqueryctl config-check
sudo tee /etc/osquery/osquery.conf > /dev/null << 'CONF'
{
  "options": {
    "config_plugin": "tls",
    "logger_plugin": "tls",
    "distributed_plugin": "tls",
    "disable_distributed": false,
    "tls_server_certs": "/var/osquery/certs/fleet.pem",
    "tls_hostname": "fleet.example.com:443",
    "enroll_secret_path": "/var/osquery/enroll_secret.txt"
  }
}
CONF

# Place the enrollment secret from Fleet's UI
echo "your-enroll-secret-here" | sudo tee /var/osquery/enroll_secret.txt
sudo systemctl start osqueryd
```

### Example Compliance Query

Fleet lets you define policies as SQL queries. Here is one that checks for disk encryption on macOS devices:

```sql
-- Policy: Full disk encryption enabled
SELECT 1 FROM disk_encryption WHERE user_uuid IS NOT NULL AND encryption_status = 'encrypted';
```

For Linux endpoints checking SSH configuration:

```sql
-- Policy: SSH root login disabled
SELECT 1 FROM ssh_configs WHERE parameter = 'PermitRootLogin' AND value = 'no';
```

## Wazuh — Unified XDR and SIEM Platform

Wazuh ([wazuh/wazuh](https://github.com/wazuh/wazuh), 15,345 stars) is the most comprehensive open-source endpoint security platform available. It combines XDR (extended detection and response), SIEM (security information and event management), and compliance monitoring in a single integrated stack.

### Key Capabilities

- **Threat detection** — signature-based and behavioral analysis for malware, rootkits, and anomalous activity
- **File integrity monitoring** — real-time alerts on critical file changes across monitored endpoints
- **Vulnerability detection** — automated CVE scanning against installed software inventories
- **Regulatory compliance** — built-in mappings for PCI DSS, HIPAA, NIST 800-53, GDPR, and TSC
- **Log analysis and correlation** — centralized log collection with rule-based alerting
- **Active response** — automated remediation actions (block IPs, restart services, run scripts)
- **Cloud security** — monitoring for AWS, Azure, and GCP workloads alongside on-premises endpoints

### Architecture

Wazuh's architecture consists of four components: the Wazuh Manager (analysis engine), Wazuh Indexer (OpenSearch-based data store), Wazuh Dashboard (visualization UI), and Wazuh Agent (lightweight endpoint collector). The full stack ships as a coordinated Docker Compose deployment.

### Docker Deployment

```yaml
# docker-compose.wazuh.yml
services:
  wazuh.manager:
    image: wazuh/wazuh-manager:5.0.0
    hostname: wazuh.manager
    restart: always
    ports:
      - "1514:1514"
      - "1515:1515"
      - "514:514/udp"
      - "55000:55000"
    environment:
      - WAZUH_INDEXER_HOSTS=wazuh.indexer:9200
      - INDEXER_USERNAME=admin
      - INDEXER_PASSWORD=SecretPassword
    volumes:
      - wazuh_api_configuration:/var/wazuh-manager/api/configuration
      - wazuh_etc:/var/wazuh-manager/etc
      - wazuh_logs:/var/wazuh-manager/logs
      - wazuh_queue:/var/wazuh-manager/queue

  wazuh.indexer:
    image: wazuh/wazuh-indexer:5.0.0
    hostname: wazuh.indexer
    restart: always
    ports:
      - "9200:9200"
    environment:
      - OPENSEARCH_INITIAL_ADMIN_PASSWORD=SecretPassword
    volumes:
      - wazuh-indexer-data:/var/lib/wazuh-indexer

  wazuh.dashboard:
    image: wazuh/wazuh-dashboard:5.0.0
    hostname: wazuh.dashboard
    restart: always
    ports:
      - "443:5601"
    depends_on:
      - wazuh.indexer
    environment:
      - WAZUH_API_URL=https://wazuh.manager
      - API_USERNAME=wazuh-wui
      - API_PASSWORD=MyS3cr37Passw0rd

volumes:
  wazuh_api_configuration:
  wazuh_etc:
  wazuh_logs:
  wazuh_queue:
  wazuh-indexer-data:
```

Start the full Wazuh stack:

```bash
docker compose -f docker-compose.wazuh.yml up -d
```

The Wazuh Dashboard is available at `https://localhost:443` with default credentials (admin / SecretPassword).

### Installing the Wazuh Agent

The Wazuh Agent runs on each endpoint and forwards security telemetry to the manager:

```bash
# Install Wazuh Agent (Ubuntu/Debian)
curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | sudo gpg --dearmor -o /usr/share/keyrings/wazuh.gpg
echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/5.x/apt/ stable main" | sudo tee /etc/apt/sources.list.d/wazuh.list
sudo apt-get update && sudo apt-get install -y wazuh-agent

# Point agent at your Wazuh Manager
sudo sed -i 's/<address>MANAGER_IP<\/address>/<address>wazuh-manager.example.com<\/address>/' \
  /var/ossec/etc/ossec.conf
sudo systemctl enable --now wazuh-agent
```

### Compliance Mapping Example

Wazuh includes built-in compliance mappings. To check PCI DSS status, query the dashboard API:

```bash
curl -k -u admin:SecretPassword \
  "https://localhost:443/security/user/authenticate?raw=true" > /tmp/wazuh_token

TOKEN=$(cat /tmp/wazuh_token)
curl -k -H "Authorization: Bearer $TOKEN" \
  "https://localhost:55000/agents?status=active&q=group=default"
```

## Teleport — Infrastructure Access with Device Trust

Teleport ([gravitational/teleport](https://github.com/gravitational/teleport), 20,164 stars) approaches endpoint management from a different angle: it is primarily an infrastructure access platform that has evolved to include device trust and endpoint posture verification. Rather than continuously monitoring every aspect of endpoint state, Teleport focuses on ensuring that only compliant, verified devices can access your infrastructure.

### Key[kubernetes](https://kubernetes.io/)ies

- **Unified access gateway** — SSH, Kubernetes, database, application, and desktop access through a single identity-aware proxy
- **Device trust** — verify endpoint posture (OS version, disk encryption, EDR status) before granting access
- **Certificate-based auth** — short-lived certificates replace static SSH keys and cloud IAM credentials
- **Session recording** — full audit trail of every SSH session, kubectl command, and database query
- **Identity integration** — connects to Okta, Active Directory, GitHub, SAML, and OIDC providers
- **Teleport Agent** — lightweight daemon for endpoint attestation and device enrollment

### Architecture

Teleport runs as a unified binary with three logical services: the Auth Service (certificate authority and identity store), the Proxy Service (external-facing access gateway), and the Node Service (runs on each target host). For device trust, the Device Agent runs on end-user machines.

### Docker Deployment

```yaml
# docker-compose.teleport.yml
services:
  teleport:
    image: public.ecr.aws/gravitational/teleport-distroless:17
    restart: always
    ports:
      - "3023:3023"   # SSH proxy
      - "3024:3024"   # SSH node proxy
      - "3025:3025"   # Auth service
      - "443:443"     # HTTPS proxy
      - "3080:3080"   # HTTP (redirects to HTTPS)
    volumes:
      - ./teleport-config:/etc/teleport
      - teleport-data:/var/lib/teleport
    command: ["teleport", "start", "--diag-addr=0.0.0.0:3000"]

  teleport-db:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_USER: teleport
      POSTGRES_PASSWORD: teleport_pass
      POSTGRES_DB: teleport
    volumes:
      - teleport-postgres:/var/lib/postgresql/data

volumes:
  teleport-data:
  teleport-postgres:
```

Create a minimal configuration file before starting:

```yaml
# teleport-config/teleport.yaml
version: v3
teleport:
  nodename: teleport.example.com
  data_dir: /var/lib/teleport
  auth_token: your-static-auth-token
  auth_servers: ["localhost:3025"]

auth_service:
  enabled: "yes"
  listen_addr: 0.0.0.0:3025
  cluster_name: teleport.example.com
  # Enable device trust
  device_trust:
    enabled: true
    mode: "enforce"

proxy_service:
  enabled: "yes"
  web_listen_addr: 0.0.0.0:443
  public_addr: teleport.example.com:443
  ssh_public_addr: teleport.example.com:3023

ssh_service:
  enabled: "yes"
  labels:
    env: production
```

Start Teleport:

```bash
mkdir -p teleport-config
# Place teleport.yaml in teleport-config/
docker compose -f docker-compose.teleport.yml up -d
```

Access the Teleport Web UI at `https://localhost:443`. Create the initial admin user:

```bash
docker compose -f docker-compose.teleport.yml exec teleport \
  tctl users add admin --roles=editor,access --logins=root,ubuntu
```

### Device Trust Enrollment

Teleport's device trust verifies endpoint posture before granting access. Enroll a device using the `tsh` CLI:

```bash
# Install tsh (macOS)
brew install teleport

# Login and enroll device
tsh login --proxy=teleport.example.com --auth=github
tsh device enroll --name=my-laptop
```

The device agent collects attestation data (TPM status, disk encryption, OS version) and reports it to the Teleport Auth Service. Access policies can then require specific device states:

```yaml
# Example role requiring encrypted devices
kind: role
version: v7
metadata:
  name: encrypted-device-only
spec:
  require_device_trust: true
  device_trust_mode: "required"
  allow:
    # Only devices with full disk encryption can access production
    rules:
      - resources: ["*"]
        verbs: ["*"]
```

## Head-to-Head Comparison

| Feature | Fleet | Wazuh | Teleport |
|---------|-------|-------|----------|
| **Primary focus** | Endpoint visibility & compliance | XDR/SIEM security monitoring | Infrastructure access & device trust |
| **Stars (GitHub)** | 6,261 | 15,345 | 20,164 |
| **Language** | Go | C/C++ | Go |
| **Agent** | osqueryd | Wazuh Agent | Teleport Device Agent |
| **Database** | MySQL | OpenSearch (Wazuh Indexer) | SQLite / PostgreSQL (backend) |
| **Live queries** | Yes (SQL via osquery) | Limited | No |
| **Threat detection** | Basic (CVE matching) | Full (signatures + behavioral) | No (access-focused) |
| **File integrity monitoring** | Via osquery queries | Native, real-time | No |
| **Compliance frameworks** | Custom SQL policies | PCI DSS, HIPAA, NIST, GDPR, TSC | Device posture policies |
| **MDM support** | Apple MDM | No | No |
| **Session recording** | No | No | Yes (SSH, K8s, DB, desktop) |
| **Certificate-based auth** | No | No | Yes (SSH, K8s, DB, apps) |
| **Device trust enforcement** | Via policy checks | Via agent compliance | Native (TPM attestation) |
| **Cloud workload support** | Yes (via osquery) | Yes (AWS, Azure, GCP) | Yes (K8s, databases, apps) |
| **Community edition limits** | None | None | Community: no device trust enforcement |
| **Docker complexity** | 3 services (Fleet + MySQL + Redis) | 3 services (Manager + Indexer + Dashboard) | 2 services (Teleport + PostgreSQL) |
| **Resource footprint** | Moderate (~1 GB RAM) | Heavy (~4 GB RAM) | Light (~512 MB RAM) |

## Which One Should You Choose?

**Choose Fleet if** your primary need is endpoint visibility and compliance auditing. Fleet's osquery foundation gives you the most granular insight into endpoint state — running processes, installed packages, network connections, user accounts — all queryable in real-time using SQL. The open-source edition includes full policy management, software inventory, and vulnerability detection. If you need to answer questions like "which servers are missing this security patch?" or "show me all machines with sudo access granted to former employees," Fleet is the most direct tool.

**Choose Wazuh if** you need comprehensive endpoint security monitoring with threat detection, file integrity monitoring, and regulatory compliance reporting. Wazuh is the heaviest of the three to deploy but also the most feature-complete for security operations. Its built-in compliance mappings for PCI DSS, HIPAA, and NIST make it the natural choice for regulated industries. If your SOC team needs a self-hosted alternative to CrowdStrike or SentinelOne, Wazuh is the closest open-source match.

**Choose Teleport if** your priority is controlling access to infrastructure based on device posture and identity. Teleport excels at replacing SSH keys, managing Kubernetes access, and ensuring that only verified, compliant devices can reach your production systems. The certificate-based authentication model eliminates the operational overhead of key rotation. If you are replacing bastion hosts, consolidating access controls across SSH/K8s/databases, or implementing zero-trust network principles, Teleport is the right foundation.

For many organizations, the ideal setup combines two of these tools: Fleet for continuous endpoint visibility paired with Teleport for access control, or Wazuh for security monitoring with Fleet for deeper compliance queries. All three can coexist since they serve complementary functions.

For related reading, see our [runtime security monitoring guide](../falco-vs-osquery-vs-auditd-self-hosted-runtime-security-guide-2026/) for a deeper look at osquery's threat detection capabilities, the [self-hosted SIEM comparison](../self-hosted-siem-wazuh-security-onion-elastic-guide/) to understand how Wazuh fits into a broader security stack, and our [SSH bastion host guide](../self-hosted-ssh-bastion-jump-server-teleport-guacamole-trysail-guide-2026/) for more on Teleport's access proxy features.

## FAQ

### Can Fleet, Wazuh, and Teleport run on the same endpoints?

Yes. Fleet uses osqueryd, Wazuh uses its own agent, and Teleport uses a device agent or node service. These are independent processes that can coexist on the same machine without conflicts. In fact, running Fleet and Wazuh together is a common pattern — Fleet handles compliance queries while Wazuh manages threat detection.

### How many endpoints can a self-hosted Fleet server manage?

A single Fleet server with MySQL and Redis can comfortably manage 10,000+ endpoints on a modern server (8 CPU cores, 32 GB RAM). For larger deployments, Fleet supports horizontal scaling with Redis clusters and MySQL read replicas. The osquery agent on each endpoint uses minimal resources — typically under 200 MB RAM and negligible CPU.

### Does Wazuh work without the full Indexer and Dashboard?

Wazuh Manager can run standalone and still receive agent data, trigger alerts, and execute active responses. However, you lose the visualization layer and the ability to search historical data. For minimal deployments, you can pair Wazuh Manager with an external log aggregator instead of the bundled OpenSearch stack.

### Is Teleport's device trust available in the open-source edition?

Teleport Community Edition includes the core access proxy, SSH/K8s/database access, and session recording. Device trust enforcement (requiring TPM attestation and disk encryption before granting access) requires Teleport Enterprise. However, the basic device enrollment and posture collection features are available in the open-source build.

### How do these tools compare to commercial products like Jamf or CrowdStrike?

Fleet covers much of Jamf's device inventory and compliance reporting functionality (plus Apple MDM). Wazuh matches CrowdStrike's endpoint detection and response capabilities with additional SIEM features. Teleport replaces bastion hosts and access management platforms like BeyondCorp. The trade-off is operational overhead — you are responsible for deployment, upgrades, and scaling rather than paying a vendor to manage the infrastructure.

### What is the minimum hardware required to evaluate these tools?

For a proof-of-concept with 5-10 test endpoints: Fleet runs on 2 CPU cores and 4 GB RAM; Wazuh needs 4 CPU cores and 8 GB RAM (the Indexer is the heaviest component); Teleport runs on 1 CPU core and 2 GB RAM. All three can run simultaneously on a single 8-core, 32 GB server for evaluation purposes.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Fleet vs Wazuh vs Teleport: Self-Hosted Endpoint Management & Device Compliance Guide 2026",
  "description": "Compare Fleet, Wazuh, and Teleport for self-hosted endpoint management, device compliance monitoring, and infrastructure access control. Complete Docker deployment guides with real configuration examples.",
  "datePublished": "2026-04-21",
  "dateModified": "2026-04-21",
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
