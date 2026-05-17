---
title: "Self-Hosted SOC Case Management: TheHive vs Cortex vs IRIS"
date: "2026-05-17"
tags: ["security", "soc", "case-management", "incident-response", "thehive", "cortex", "iris", "self-hosted"]
draft: false
---

When a security incident strikes — a compromised endpoint, a suspicious login pattern, or a confirmed data breach — your SOC team needs more than just alerts. They need a structured way to track investigations, coordinate analysis, assign tasks, and document every step of the response. That's what a **SOC case management platform** provides.

While commercial platforms like Splunk SOAR and Palo Alto Cortex XSOAR dominate the enterprise market, three powerful open-source alternatives let you build a capable SOC operations center without licensing costs or vendor lock-in: **TheHive**, **Cortex**, and **IRIS**.

This guide compares all three platforms — their architectures, features, deployment options, and how they complement each other in a complete security operations workflow.

## What Is SOC Case Management?

A Security Operations Center (SOC) case management platform is the central hub where security analysts:

- **Create and track cases** — every incident gets a unique ticket with severity, status, and assignee
- **Collect evidence** — attach IOCs (Indicators of Compromise), file samples, network captures, and logs
- **Coordinate analysis** — assign tasks to team members, track progress, and maintain an audit trail
- **Run observable analysis** — check IP addresses, domain names, file hashes, and URLs against threat intelligence feeds
- **Generate reports** — produce post-incident summaries, compliance reports, and metrics for management

Without case management, security investigations become chaotic — information scattered across Slack messages, spreadsheets, and email threads. A dedicated platform brings structure, accountability, and repeatability to the response process.

## TheHive: The Collaborative Security Platform

TheHive is the most well-known open-source SOC case management platform. Developed by CERT-FR (the French government's computer emergency response team) and now maintained by StrangeBee, TheHive provides a comprehensive web interface for security incident tracking.

**Key characteristics:**

- **Case-centric design** — every incident is a case with customizable workflows and statuses
- **Observable management** — attach IOCs (IPs, domains, hashes, URLs) to cases for analysis
- **Task management** — assign and track investigation tasks within cases
- **Template system** — pre-define case templates for common incident types (phishing, malware, intrusion)
- **Alert ingestion** — receive alerts from SIEM systems, IDS/IPS, and monitoring tools
- **Multi-tenant support** — isolate cases and data between different teams or customers
- **API-first** — full REST API for automation and integration

### Docker Deployment

```yaml
version: '3'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - es_data:/usr/share/elasticsearch/data

  cassandra:
    image: cassandra:4.1
    volumes:
      - cassandra_data:/var/lib/cassandra
    environment:
      - MAX_HEAP_SIZE=512M
      - HEAP_NEWSIZE=256M

  thehive:
    image: strangebee/thehive:5.2
    ports:
      - "9000:9000"
    depends_on:
      - elasticsearch
      - cassandra
    environment:
      - http.port=9000
    volumes:
      - ./thehive.conf:/etc/thehive/application.conf
```

### TheHive Case Workflow

1. **Alert received** — from SIEM, email gateway, or manual entry
2. **Case created** — alert promoted to a case with assigned analyst
3. **Observables added** — IP addresses, file hashes, URLs extracted from the alert
4. **Analysis run** — observables checked against threat intelligence (via Cortex)
5. **Tasks completed** — analyst documents findings, escalates if needed
6. **Case closed** — summary written, lessons captured, metrics recorded

## Cortex: The Observable Analysis Engine

Cortex is the companion analysis engine to TheHive. While TheHive manages the case workflow, Cortex performs the heavy lifting of analyzing IOCs — checking IP addresses against threat intelligence feeds, scanning files with antivirus engines, querying WHOIS databases, and running sandbox analyses.

**Key characteristics:**

- **Analyzer framework** — 100+ analyzers for checking IOCs against external services
- **Responder framework** — automated actions (block IP, quarantine host, send notification)
- **Integration with TheHive** — analysis results flow directly back into TheHive cases
- **Standalone API** — can be used independently of TheHive via REST API
- **Multi-engine support** — run the same observable through multiple analyzers simultaneously

### Docker Deployment

```yaml
version: '3'
services:
  cortex:
    image: thehiveproject/cortex:3.2
    ports:
      - "9001:9001"
    volumes:
      - ./cortex.conf:/etc/cortex/application.conf
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - http.port=9001
```

Cortex analyzers are installed as Python packages and configured through the web interface:

```ini
# Sample Cortex configuration
playout {
  analyzers = [
    "Abuse_Finder_3_0",
    "CyberCrime_Tracker",
    "MISP_2_1",
    "OTXQuery_2_0",
    "VirusTotal_GetReport_3_1",
    "Shodan_DNSResolve_1_0"
  ]
  responders = [
    "TheHive_NewCase",
    "TheHive_UpdateCase",
    "SendEmail"
  ]
}
```

## IRIS: Collaborative Incident Response Platform

IRIS (Incident Response Investigation System) is a newer entrant in the SOC case management space, designed from the ground up for collaborative incident response. Developed by the DFIR community, IRIS focuses on providing a modern, intuitive interface for managing security investigations.

**Key characteristics:**

- **Investigation-centric** — cases structured around the investigation lifecycle
- **IOC management** — dedicated IOC tracking with severity scoring and contextual enrichment
- **Evidence timeline** — visual timeline of events for chronological analysis
- **User-friendly interface** — modern web UI with intuitive navigation
- **Case collaboration** — real-time collaboration features for distributed teams
- **DFIR-focused** — built by digital forensics professionals for incident responders

### Docker Deployment

```yaml
version: '3'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: iris_db
      POSTGRES_USER: iris
      POSTGRES_PASSWORD: iris_secret
    volumes:
      - pg_data:/var/lib/postgresql/data

  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"

  iris-web:
    image: dfir-iris/iris-web:latest
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - rabbitmq
    environment:
      - IRIS_POSTGRES_HOST=postgres
      - IRIS_POSTGRES_USER=iris
      - IRIS_POSTGRES_PASSWORD=iris_secret
      - IRIS_RABBITMQ_HOST=rabbitmq
    volumes:
      - iris_data:/app/user_data
```

## Comparison Table

| Feature | TheHive | Cortex | IRIS |
|---------|---------|--------|------|
| **Primary Role** | Case management | Observable analysis | Incident response platform |
| **Architecture** | Scala/Play Framework | Python/Play Framework | Python/Flask |
| **Database** | Cassandra + Elasticsearch | Elasticsearch | PostgreSQL |
| **Case Templates** | Yes, customizable | N/A (analysis engine) | Yes, investigation-focused |
| **Observable Analysis** | Via Cortex integration | Core feature (100+ analyzers) | Built-in IOC analysis |
| **Threat Intel Feeds** | Via Cortex analyzers | Native (VirusTotal, OTX, MISP) | Built-in IOC enrichment |
| **Task Management** | Yes, within cases | N/A | Yes, investigation tasks |
| **Multi-tenancy** | Yes (organizations) | No | Yes (cases can be isolated) |
| **API** | Full REST API | Full REST API | Full REST API |
| **Web UI** | Comprehensive | Analysis dashboard | Modern investigation UI |
| **Evidence Timeline** | Basic (case notes) | N/A | Dedicated timeline view |
| **Alert Ingestion** | Yes (from SIEM, email) | Via TheHive | Manual and API |
| **GitHub Stars** | ~14,500 | ~1,579 | ~1,491 |
| **Last Updated** | Active (2025) | Active (2026) | Active (2026) |

## How These Tools Work Together

In practice, TheHive and Cortex are designed to work together as a complete SOC platform:

1. **TheHive** receives an alert and creates a case
2. Analysts add observables (IPs, hashes, domains) to the case
3. TheHive sends observables to **Cortex** for automated analysis
4. Cortex runs the IOCs through multiple analyzers (VirusTotal, Shodan, MISP)
5. Analysis results flow back into TheHive for analyst review
6. **IRIS** can serve as an alternative or complementary platform for teams that prefer its investigation-centric workflow

Many SOCs run all three: TheHive+Cortex for day-to-day case management, and IRIS for complex investigations that benefit from its timeline and evidence management features.

## When to Choose Each

### Choose TheHive (+ Cortex) when:

- You need a **mature, well-documented** case management platform
- Your team benefits from **100+ pre-built analyzers** for IOC analysis
- You want **tight SIEM integration** — TheHive can ingest alerts from most major platforms
- You need **multi-tenancy** for managing cases across multiple teams or customers
- You value a **large community** and extensive third-party integrations

### Choose IRIS when:

- You want a **modern, intuitive interface** for incident investigations
- Your team focuses on **digital forensics and incident response** (DFIR)
- You need a **visual evidence timeline** for chronological analysis
- You prefer **PostgreSQL** over Cassandra for your data layer
- You want a platform designed **by DFIR practitioners, for DFIR practitioners**

### Use Both when:

- Your SOC handles both **high-volume alert triage** (TheHive) and **complex investigations** (IRIS)
- You want Cortex's **extensive analyzer library** alongside IRIS's investigation workflow
- Different teams within your organization have **different operational preferences**

## Why Self-Host Your SOC Case Management Platform?

Security incident data is among the most sensitive information an organization handles. Self-hosting case management ensures that IOCs, investigation details, and evidence never leave your infrastructure. For regulated industries and government organizations, this is often a compliance requirement.

Self-hosted platforms also give you complete control over customization — custom case templates, proprietary analyzers, and integrations with your existing security toolchain. You're not constrained by vendor roadmaps or per-seat licensing that can become prohibitively expensive as your SOC team grows.

For teams building a complete security operations stack, our guide on [self-hosted SIEM platforms](../self-hosted-siem-wazuh-security-onion-elastic-guide/) covers the detection and alerting layer that feeds into case management. If you're also evaluating threat hunting tools, our [Velociraptor vs GRR vs Osquery comparison](/) covers the endpoint visibility side. And for automated security response, the [Shuffle SOAR vs StackStorm vs IRIS guide](/) explores orchestration options.

For teams evaluating complementary security tools, our guide on [self-hosted SIEM platforms](../self-hosted-siem-wazuh-security-onion-elastic-guide/) covers the detection layer, while the [Shuffle SOAR vs StackStorm vs IRIS comparison](../2026-04-20-shuffle-soar-vs-stackstorm-vs-iris-security-automation-incident-response-guide-2026/) explores orchestration options.
## FAQ

### Can TheHive and Cortex run independently?

Yes. TheHive can function as a standalone case management system without Cortex, and Cortex can be used independently via its REST API. However, they are designed to work together — TheHive's observable analysis features require a Cortex instance to perform automated IOC checks.

### Does IRIS replace TheHive?

IRIS serves a similar purpose but with a different focus. TheHive is optimized for high-volume case management and alert triage, while IRIS is designed for deep-dive incident investigations. Many teams use both, routing initial triage through TheHive and complex investigations through IRIS.

### What threat intelligence feeds does Cortex support?

Cortex supports 100+ analyzers including VirusTotal, AlienVault OTX, MISP, Shodan, AbuseIPDB, IBM X-Force, and many more. Analyzers cover IP reputation, domain analysis, file scanning, URL checking, and threat intelligence lookups. New analyzers can be developed using the Cortex analyzer SDK.

### Can I migrate cases from TheHive to IRIS?

There is no official migration tool, but both platforms expose full REST APIs. Custom migration scripts can export cases from TheHive and import them into IRIS. The data models differ significantly — TheHive uses a case/observable/task structure while IRIS uses an investigation/IOC/timeline structure — so manual mapping is typically required.

### What database does TheHive require?

TheHive 5.x requires both Cassandra (for case data) and Elasticsearch (for search and indexing). This dual-database architecture provides fast case retrieval and powerful search capabilities but adds operational complexity compared to single-database platforms like IRIS (PostgreSQL only).

### Is Cortex required for TheHive to function?

No. TheHive functions as a complete case management system without Cortex. However, without Cortex, you lose automated observable analysis — analysts would need to manually check IOCs against threat intelligence services rather than having Cortex run hundreds of analyzers automatically.

## Choosing the Right SOC Case Management Platform

TheHive+Cortex remains the most comprehensive open-source SOC platform, with mature case management and the widest analyzer ecosystem. IRIS offers a modern, investigation-focused alternative that appeals to DFIR teams. For organizations evaluating their security operations tooling, running both platforms in parallel — TheHive for alert triage and IRIS for deep investigations — provides the best of both worlds.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SOC Case Management: TheHive vs Cortex vs IRIS",
  "description": "Compare TheHive, Cortex, and IRIS for self-hosted SOC case management. Includes Docker deployment, features comparison, and decision guide.",
  "datePublished": "2026-05-17",
  "dateModified": "2026-05-17",
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
