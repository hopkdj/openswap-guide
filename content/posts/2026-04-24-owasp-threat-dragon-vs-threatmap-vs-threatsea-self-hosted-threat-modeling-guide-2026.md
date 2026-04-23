---
title: "OWASP Threat Dragon vs ThreatMap vs ThreatSea: Self-Hosted Threat Modeling Guide 2026"
date: 2026-04-24
tags: ["comparison", "guide", "self-hosted", "security", "threat-modeling"]
draft: false
description: "Compare three open-source threat modeling tools — OWASP Threat Dragon, ThreatMap, and ThreatSea — for self-hosted deployment. Includes Docker setup, STRIDE analysis, and hands-on configuration."
---

Threat modeling is a systematic process for identifying, assessing, and mitigating security risks in software architecture before code is written. By applying structured methodologies like STRIDE, MITRE ATT&CK, and PASTA, teams can uncover design-level vulnerabilities early — when they are cheapest to fix.

Self-hosting threat modeling tools keeps your architecture diagrams and threat analyses inside your own infrastructure. For organizations handling sensitive systems, regulated workloads, or internal network designs, running threat modeling on-premises eliminates the risk of exposing proprietary system designs to third-party SaaS platforms.

This guide compares three open-source, self-hostable threat modeling tools: **OWASP Threat Dragon**, **ThreatMap**, and **ThreatSea**. Each takes a different approach — from visual diagramming to infrastructure-as-code scanning to methodology-driven analysis.

## Why Self-Host Your Threat Modeling Tools

Threat modeling requires detailed knowledge of your system architecture — data flows, trust boundaries, external dependencies, and authentication patterns. Sharing this information with cloud-hosted services introduces several concerns:

- **Data sovereignty**: Architecture diagrams reveal internal network topology and system interconnections
- **Compliance requirements**: Regulated industries (finance, healthcare, government) often restrict where system design data can be stored
- **Air-gapped environments**: Organizations operating isolated networks cannot reach external SaaS platforms
- **Cost control**: Per-seat SaaS licensing for threat modeling tools can scale quickly as teams grow
- **Customization**: Self-hosted tools can be extended with custom threat catalogs, internal compliance rules, and organization-specific risk scoring

For organizations already running self-hosted security infrastructure — such as [vulnerability management platforms](../2026-04-20-defectdojo-vs-greenbone-vs-faraday-self-hosted-vulnerability-management-2026/) or [self-hosted WAF solutions](../2026-04-18-bunkerweb-vs-modsecurity-vs-crowdsec-self-hosted-waf-guide-2026/) — adding threat modeling to the same infrastructure creates a cohesive security workflow.

## OWASP Threat Dragon

[OWASP Threat Dragon](https://github.com/OWASP/threat-dragon) is the most established open-source threat modeling tool, maintained under the OWASP umbrella. It provides a web-based interface for creating threat model diagrams using standard methodologies.

**GitHub stats**: 1,440 stars · JavaScript · Last updated: April 22, 2026

### Key Features

- **STRIDE methodology**: Built-in threat categorization using Microsoft's STRIDE model (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege)
- **Visual diagram editor**: Drag-and-drop interface for creating data flow diagrams with trust boundaries, processes, data stores, and external entities
- **Multiple data flow diagram (DFD) pages**: Support for multi-page threat models within a single project
- **JSON-based storage**: Models saved as JSON files, making them version-control friendly
- **Desktop and web versions**: Available as a standalone desktop application (Electron) and a web application
- **Import/export**: Supports importing from previous Threat Dragon versions and exporting reports

### Docker Installation

OWASP Threat Dragon does not provide an official Docker Compose file in its repository, but it can be containerized using the included Dockerfile. The web version is a Node.js application:

```bash
# Build and run OWASP Threat Dragon from source
git clone https://github.com/OWASP/threat-dragon.git
cd threat-dragon

# Build the Docker image
docker build -t threat-dragon .

# Run the container
docker run -d \
  --name threat-dragon \
  -p 3000:3000 \
  -e NODE_ENV=production \
  threat-dragon
```

For production deployments, pair with a reverse proxy and persistent storage:

```yaml
# docker-compose.yml for Threat Dragon with Nginx reverse proxy
version: "3.8"
services:
  threat-dragon:
    build:
      context: .
      dockerfile: Dockerfile
    restart: unless-stopped
    environment:
      - NODE_ENV=production
      - ENCRYPTION_KEY=your-encryption-key-here
    volumes:
      - threat-dragon-data:/app/data
    networks:
      - td-network

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - threat-dragon
    networks:
      - td-network

networks:
  td-network:
    driver: bridge

volumes:
  threat-dragon-data:
```

The `ENCRYPTION_KEY` environment variable is used to encrypt session data and should be a strong, randomly generated string. Store your threat model JSON files in a Git repository for version tracking and team collaboration.

### Strengths

- **Largest community**: 1,440+ GitHub stars means more tutorials, plugins, and community support
- **OWASP backing**: Part of the OWASP project ecosystem, ensuring long-term maintenance and alignment with industry standards
- **Mature STRIDE integration**: Deep STRIDE support with automatic threat generation based on diagram element types
- **Active development**: Consistently updated with new features and security patches

### Limitations

- **No built-in database**: Requires manual file management or integration with GitHub for model storage
- **Limited framework support**: Primarily focused on STRIDE; no native MITRE ATT&CK or PASTA support
- **Manual deployment**: No official Docker Compose means more setup work for production environments

## ThreatMap

[ThreatMap](https://github.com/bogdanticu88/threatmap) takes a different approach — instead of manual diagramming, it analyzes infrastructure-as-code (IaC) files to automatically generate threat models. This makes it ideal for DevOps teams who want threat modeling integrated into their CI/CD pipelines.

**GitHub stats**: 56 stars · Python · Last updated: March 25, 2026

### Key Features

- **Multi-framework support**: STRIDE, MITRE ATT&CK, and PASTA methodologies out of the box
- **IaC scanning**: Analyzes Terraform, CloudFormation, and Kubernetes manifests to identify threats
- **REST API and GraphQL**: Programmatic access for integration with CI/CD pipelines and security dashboards
- **Docker support**: Containerized deployment with a single command
- **Automated threat generation**: Scans infrastructure definitions and maps findings to known threat patterns
- **Report generation**: Produces structured threat reports with severity ratings and mitigation recommendations

### Docker Installation

ThreatMap provides a Dockerfile for straightforward containerized deployment:

```bash
# Clone and build
git clone https://github.com/bogdanticu88/threatmap.git
cd threatmap

# Build the Docker image
docker build -t threatmap .

# Run with API access
docker run -d \
  --name threatmap \
  -p 8080:8080 \
  -v ./scans:/app/scans \
  threatmap
```

For a production setup with persistent scan storage:

```yaml
# docker-compose.yml for ThreatMap
version: "3.8"
services:
  threatmap:
    build:
      context: .
      dockerfile: Dockerfile
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - threatmap-scans:/app/scans
      - ./terraform-configs:/app/input:ro
    environment:
      - SCAN_INTERVAL=3600
      - REPORT_FORMAT=json
    security_opt:
      - no-new-privileges:true

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis-data:/data
    security_opt:
      - no-new-privileges:true

networks:
  default:
    driver: bridge

volumes:
  threatmap-scans:
  redis-data:
```

### Using the REST API

ThreatMap exposes a REST API for programmatic threat analysis:

```bash
# Submit a Terraform file for scanning
curl -X POST http://localhost:8080/api/v1/scan \
  -H "Content-Type: multipart/form-data" \
  -F "file=@infrastructure.tf" \
  -F "framework=STRIDE"

# Check scan status
curl http://localhost:8080/api/v1/scans/<scan-id>/status

# Retrieve results
curl http://localhost:8080/api/v1/scans/<scan-id>/results \
  | jq '.threats[] | {category, severity, description}'
```

### Strengths

- **Automation-first**: Designed for pipeline integration rather than manual use
- **Three frameworks**: Only tool in this comparison supporting STRIDE, MITRE ATT&CK, and PASTA simultaneously
- **IaC-native**: Scans actual infrastructure definitions rather than abstract diagrams
- **API-driven**: REST and GraphQL interfaces enable integration with existing security tooling

### Limitations

- **Smaller community**: 56 stars means fewer community resources and slower issue resolution
- **Less visual**: No drag-and-drop diagram editor; output is primarily structured data and reports
- **Python dependency**: Requires Python 3.11+ runtime for builds

## ThreatSea

[ThreatSea](https://github.com/MaibornWolff/ThreatSea) implements the 4x6 threat modeling methodology — a structured approach that maps six threat categories (from STRIDE) against four system elements (processes, data stores, data flows, and external entities). It provides a modern web interface with database-backed storage.

**GitHub stats**: 24 stars · TypeScript · Last updated: April 23, 2026

### Key Features

- **4x6 methodology**: Systematic threat analysis mapping STRIDE categories to system components
- **PostgreSQL storage**: Database-backed model storage with proper access control
- **Modern TypeScript stack**: Built with Node.js, Express, and React for a responsive user experience
- **Official Docker Compose**: One-command deployment with PostgreSQL included
- **Fixed authentication**: Supports fixed-user authentication for single-tenant deployments
- **JWT-based sessions**: Secure session management with configurable token secrets

### Docker Installation

ThreatSea provides an official Docker Compose file, making it the easiest of the three to deploy:

```yaml
# docker-compose.yml for ThreatSea (from official repo)
services:
  postgres:
    image: postgres:18.3-alpine
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U threatsea -d threatsea"]
      interval: 5s
      timeout: 5s
      retries: 3
    environment:
      POSTGRES_DB: threatsea
      POSTGRES_USER: threatsea
      POSTGRES_PASSWORD: "threatseapassword"
    security_opt:
      - no-new-privileges:true
    volumes:
      - threatsea_data:/var/lib/postgresql/data
    networks:
      - threatsea

  threatsea:
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    build:
      context: .
      dockerfile: "./Dockerfile"
    environment:
      JWT_SECRET: "somerandomstringtobeusedasJWTsecret"
      EXPRESS_SESSION_SECRET: "someRandomExpressSessionSecret"
      AUTH_METHOD: fixed
      ORIGIN_APP: "http://127.0.0.1:8000"
      ORIGIN_BACKEND: "http://127.0.0.1:8000"
      LOG_LEVEL: 0
      DATABASE_HOST: postgres
      DATABASE_USER: threatsea
      DATABASE_PASSWORD: "threatseapassword"
      DATABASE_NAME: threatsea
      DATABASE_TLS: disabled
      COOKIES_SECURE_OPTION: disabled
    security_opt:
      - no-new-privileges:true
    ports:
      - "8000:8000"
    networks:
      - threatsea

networks:
  threatsea:

volumes:
  threatsea_data:
```

Before deploying to production, replace the placeholder secrets:

```bash
# Generate secure secrets
JWT_SECRET=$(openssl rand -base64 32)
SESSION_SECRET=$(openssl rand -base64 32)
DB_PASSWORD=$(openssl rand -base64 24)

# Start with production secrets
docker compose up -d
```

For TLS-secured deployment, update the environment variables and add an Nginx reverse proxy:

```bash
# Enable database TLS
DATABASE_TLS=enabled
COOKIES_SECURE_OPTION=enabled

# Set production origins
ORIGIN_APP=https://threatsea.yourdomain.com
ORIGIN_BACKEND=https://threatsea.yourdomain.com
```

### The 4x6 Methodology

ThreatSea's 4x6 approach provides a more structured analysis than freeform diagramming:

| Threat Category | Process | Data Store | Data Flow | External Entity |
|---|---|---|---|---|
| **Spoofing** | Identity verification for processes | Stored credential protection | Connection authentication | Entity identity validation |
| **Tampering** | Process integrity controls | Data integrity checks | Message integrity | Input validation |
| **Repudiation** | Process audit logging | Data access logging | Transaction logging | Authentication logging |
| **Information Disclosure** | Process data isolation | Data encryption at rest | Transport encryption | Access control |
| **Denial of Service** | Process resource limits | Storage quotas | Rate limiting | Request filtering |
| **Elevation of Privilege** | Least privilege enforcement | Access control lists | Secure channel enforcement | Permission validation |

This matrix approach ensures that every system component is evaluated against every relevant threat category — reducing the chance of oversight compared to freeform analysis.

### Strengths

- **Easiest deployment**: Official Docker Compose with PostgreSQL, ready in minutes
- **Structured methodology**: 4x6 matrix ensures comprehensive coverage
- **Database-backed**: Persistent storage with proper concurrent access
- **Actively maintained**: Updated as recently as April 23, 2026

### Limitations

- **Smallest community**: 24 stars means limited third-party documentation
- **Single methodology**: Only supports the 4x6 approach; no native MITRE ATT&CK or PASTA
- **Fixed authentication**: Only supports single-user/fixed auth; no LDAP or SSO integration yet

## Comparison Table

| Feature | OWASP Threat Dragon | ThreatMap | ThreatSea |
|---|---|---|---|
| **GitHub Stars** | 1,440 | 56 | 24 |
| **Language** | JavaScript | Python | TypeScript |
| **Last Updated** | Apr 2026 | Mar 2026 | Apr 2026 |
| **Primary Approach** | Visual diagramming | IaC scanning | 4x6 methodology matrix |
| **STRIDE Support** | ✅ Native | ✅ Native | ✅ Via 4x6 matrix |
| **MITRE ATT&CK** | ❌ | ✅ Native | ❌ |
| **PASTA Framework** | ❌ | ✅ Native | ❌ |
| **Docker Compose** | ❌ Manual | ❌ Manual | ✅ Official |
| **Database Storage** | ❌ JSON files | ❌ File-based | ✅ PostgreSQL |
| **Visual Editor** | ✅ Drag-and-drop | ❌ API/report-based | ✅ Web interface |
| **REST API** | ❌ | ✅ REST + GraphQL | ❌ |
| **IaC Scanning** | ❌ | ✅ Terraform, CFN, K8s | ❌ |
| **Team Collaboration** | Via Git | Via API | Via database |
| **CI/CD Integration** | Limited | ✅ Pipeline-ready | Limited |

## Choosing the Right Tool

The best threat modeling tool depends on your team's workflow and requirements:

**Choose OWASP Threat Dragon if:**
- You need a visual, diagram-based threat modeling experience
- You want the largest community and most documentation
- STRIDE methodology is sufficient for your needs
- You prefer to store models as version-controlled JSON files

**Choose ThreatMap if:**
- You want automated threat analysis of infrastructure-as-code
- You need multiple frameworks (STRIDE + MITRE ATT&CK + PASTA)
- You plan to integrate threat modeling into CI/CD pipelines
- You prefer API-driven workflows over visual editors

**Choose ThreatSea if:**
- You want the simplest deployment with Docker Compose
- You prefer structured, methodology-driven analysis (4x6 matrix)
- You need database-backed storage with concurrent access
- You want a modern TypeScript stack with PostgreSQL

## Next Steps

Regardless of which tool you choose, threat modeling should be integrated into your broader security workflow. Consider pairing your threat modeling tool with:

- [Vulnerability management platforms](../2026-04-20-defectdojo-vs-greenbone-vs-faraday-self-hosted-vulnerability-management-2026/) to track identified threats through remediation
- [Container and Kubernetes hardening tools](../2026-04-20-kube-bench-vs-trivy-vs-kubescape-container-kubernetes-hardening-guide-2026/) to validate that mitigations are properly implemented
- A web application firewall like [BunkerWeb or ModSecurity](../2026-04-18-bunkerweb-vs-modsecurity-vs-crowdsec-self-hosted-waf-guide-2026/) as a compensating control for threats that cannot be eliminated at the design level

Regular threat modeling sessions — ideally at the start of each major feature development cycle — help catch architectural security issues before they become expensive to fix.

## FAQ

### What is threat modeling and why is it important?

Threat modeling is a structured approach to identifying and mitigating security risks in software systems during the design phase. Rather than finding bugs in written code, threat modeling examines the system architecture to identify design-level vulnerabilities. Early threat modeling is significantly cheaper than post-deployment remediation — fixing a design flaw during architecture review costs roughly 30x less than fixing the same issue after deployment.

### What is the STRIDE methodology?

STRIDE is a threat categorization model developed by Microsoft that classifies threats into six categories: **S**poofing (identity impersonation), **T**ampering (unauthorized data modification), **R**epudiation (denying an action), **I**nformation Disclosure (data exposure), **D**enial of Service (service disruption), and **E**levation of Privilege (gaining unauthorized access). It is the most widely used threat modeling methodology and is supported by all three tools in this comparison.

### Can I use these tools in an air-gapped environment?

Yes. All three tools — OWASP Threat Dragon, ThreatMap, and ThreatSea — can be deployed entirely self-hosted with no external dependencies once container images are pulled. For air-gapped environments, pull Docker images on an internet-connected machine, save them with `docker save`, transfer via secure media, and load with `docker load`. None of the tools require outbound network access for core functionality.

### How does ThreatMap differ from OWASP Threat Dragon?

ThreatMap and OWASP Threat Dragon serve different workflows. Threat Dragon is a visual, diagram-based tool where users manually create data flow diagrams and annotate threats. ThreatMap is automation-focused — it scans infrastructure-as-code files (Terraform, CloudFormation, Kubernetes manifests) and automatically generates threat reports using multiple frameworks. Use Threat Dragon for design-time manual analysis and ThreatMap for continuous, pipeline-integrated scanning of deployed infrastructure.

### What is the 4x6 methodology used by ThreatSea?

The 4x6 methodology maps six threat categories (STRIDE: Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) against four system elements (Processes, Data Stores, Data Flows, External Entities). This creates a 24-cell matrix that ensures every component is evaluated against every relevant threat type. The structured approach reduces the chance of missing threats compared to freeform brainstorming.

### Do these tools support team collaboration?

OWASP Threat Dragon supports collaboration indirectly through Git — since models are stored as JSON files, teams can use version control for concurrent work. ThreatSea provides database-backed storage with concurrent user access. ThreatMap offers the most integration-friendly approach with REST and GraphQL APIs, allowing teams to build custom dashboards and integrate with existing collaboration platforms.

### How often should I run threat modeling sessions?

Threat modeling should be performed at the beginning of each major feature development cycle, during architectural design reviews, and whenever significant infrastructure changes are planned. For automated tools like ThreatMap, continuous scanning can be integrated into CI/CD pipelines to detect new threats whenever infrastructure-as-code changes are committed.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "OWASP Threat Dragon vs ThreatMap vs ThreatSea: Self-Hosted Threat Modeling Guide 2026",
  "description": "Compare three open-source threat modeling tools — OWASP Threat Dragon, ThreatMap, and ThreatSea — for self-hosted deployment. Includes Docker setup, STRIDE analysis, and hands-on configuration.",
  "datePublished": "2026-04-24",
  "dateModified": "2026-04-24",
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
