---
title: "Self-Hosted Firewall Policy Management: Capirca vs Aerleon vs Firewall Orchestrator (2026)"
date: "2026-05-14"
tags: ["firewall", "network-security", "policy-as-code", "automation", "self-hosted"]
draft: false
---

Managing firewall rules across multiple vendors and cloud platforms is one of the most error-prone tasks in infrastructure operations. Manual configuration leads to stale rules, security gaps, and compliance violations. Firewall policy management tools solve this by providing a centralized, code-driven approach to defining, generating, and auditing access control lists (ACLs) across heterogeneous environments.

In this guide, we compare three open-source solutions for self-hosted firewall policy management: **Capirca** (Google multi-platform ACL generator), **Aerleon** (its actively maintained successor), and **Firewall Orchestrator** (a comprehensive rule management and compliance platform). Each takes a different approach to the problem — from policy-as-code generation to full lifecycle rule management.

## What Is Firewall Policy Management?

Firewall policy management tools centralize the definition and deployment of network security rules across multiple vendors (Cisco ASA, Juniper SRX, Palo Alto Networks, iptables, nftables, AWS Security Groups, and more). Instead of configuring each firewall individually through its own CLI or web interface, you define policies in a unified format and let the tool generate vendor-specific configurations.

Key capabilities include:

- **Policy abstraction** — define rules in a vendor-neutral language
- **Multi-vendor output** — generate configs for Cisco, Juniper, Palo Alto, iptables, AWS, GCP, and more
- **Change management** — track rule modifications, approvals, and deployments
- **Compliance auditing** — detect redundant, shadowed, or overly permissive rules
- **Documentation** — auto-generate rule documentation and network diagrams

## Capirca: Google Multi-Platform ACL Generator

[Capirca](https://github.com/google/capirca) (852 GitHub stars) is an open-source ACL generation system developed by Google. It converts human-readable policy definitions into vendor-specific firewall configurations. Capirca has been used at Google scale to manage thousands of firewall rules across diverse network equipment.

### Key Features

- **Policy definition language** — define networks, services, and rules in a Python-based DSL
- **Broad vendor support** — generates configs for Cisco ASA, Juniper SRX, Palo Alto, iptables, nftables, Arista, AWS, GCP, and 20+ platforms
- **Include/exclude logic** — support for complex rule inheritance and exclusion patterns
- **Service definition sharing** — centralize port/protocol definitions across all policies
- **YAML and native format** — supports both Capirca native policy format and YAML input

### Architecture

Capirca uses a three-tier model:

1. **Network definitions** — define IP prefixes, subnets, and FQDNs in network files
2. **Service definitions** — define port/protocol combinations (e.g., `web = tcp 80, 443`)
3. **Policy files** — combine networks and services into permit/deny rules with logging options

The policy compiler then translates these definitions into vendor-specific syntax.

### Docker Deployment

Capirca is a Python library, typically deployed as a CI/CD pipeline component. Here is a containerized deployment for running Capirca as a policy generation service:

```yaml
services:
  capirca:
    image: python:3.11-slim
    working_dir: /app
    volumes:
      - ./policies:/app/policies
      - ./defs:/app/defs
      - ./output:/app/output
    command: >
      bash -c "
        pip install capirca &&
        python -m capirca.lib.capirca -p /app/policies -d /app/defs -o /app/output
      "
    restart: unless-stopped
```

Place your policy files in `./policies/`, network/service definitions in `./defs/`, and generated configs will appear in `./output/`.

### Installation

```bash
pip install capirca

# Generate configs for all platforms
python -m capirca.lib.capirca \
  --policy_file policies/example.pol \
  --network_file defs/networks.def \
  --service_file defs/services.def \
  --output_file output/cisco_acl.txt
```

## Aerleon: The Capirca Successor

[Aerleon](https://github.com/aerleon/aerleon) (244 GitHub stars) is a fork and successor to Capirca, maintained by former Capirca contributors. It adds significant improvements including YAML-based policy definitions, a richer plugin architecture, and better documentation. Aerleon is the recommended choice for new deployments.

### Key Features

- **YAML-first policies** — define rules in clean YAML instead of Capirca custom DSL
- **Enhanced plugin system** — easier to add custom output generators
- **Improved validation** — stricter policy validation with detailed error messages
- **Backwards compatible** — can read existing Capirca policy files
- **Active development** — regular releases and responsive maintainers
- **CI/CD integration** — pre-built GitHub Actions workflows for policy validation

### YAML Policy Example

```yaml
filters:
  - header:
      comment: "Allow web traffic to production servers"
      targets:
        cisco: production-acl
    terms:
      - name: allow-web
        comment: "HTTP and HTTPS from office networks"
        source-address: OFFICE_NETS
        destination-address: PROD_SERVERS
        protocol: tcp
        destination-port: [80, 443]
        action: accept
      - name: deny-all
        comment: "Default deny"
        action: deny
```

### Docker Deployment

Aerleon can be containerized for CI/CD or standalone use:

```yaml
services:
  aerleon:
    image: python:3.12-slim
    working_dir: /app
    volumes:
      - ./policies:/app/policies:ro
      - ./output:/app/output
    command: >
      bash -c "
        pip install aerleon &&
        aerleon --policy ./policies --output ./output
      "
    restart: unless-stopped
```

For CI/CD integration, add this to your GitHub Actions workflow:

```yaml
jobs:
  validate-firewall-policies:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate policies
        run: |
          pip install aerleon
          aerleon --policy ./policies --output ./output --validate-only
```

## Firewall Orchestrator: Comprehensive Rule Lifecycle Management

[Firewall Orchestrator](https://github.com/CactuseSecurity/firewall-orchestrator) (54 GitHub stars) by CactuseSecurity takes a fundamentally different approach. Instead of generating configs from abstract policies, it imports existing firewall rules from multiple vendors, normalizes them into a unified format, and provides tools for analysis, compliance checking, and change management.

### Key Features

- **Multi-vendor import** — import rules from Cisco ASA, Fortinet, Palo Alto, Check Point, and more
- **Rule normalization** — convert all rules into a common format for unified analysis
- **Compliance checking** — verify rules against security policies and regulatory frameworks
- **Change management workflow** — request, approve, and track rule changes
- **Visualization** — generate network topology and rule dependency diagrams
- **Reporting** — automated compliance reports and audit trails

### Architecture

Firewall Orchestrator uses a Django-based web application with PostgreSQL backend:

- **Importer modules** — parse vendor-specific rule exports (CSV, XML, API)
- **Normalization engine** — map vendor-specific syntax to a common rule format
- **Analysis engine** — detect shadowed rules, redundant entries, and policy violations
- **Web UI** — rule browsing, search, approval workflows, and reporting

### Docker Compose Deployment

Firewall Orchestrator ships with Ansible deployment roles. Here is a Docker Compose setup:

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: fwo
      POSTGRES_USER: fwo
      POSTGRES_PASSWORD: fwo_secure_password
    volumes:
      - pgdata:/var/lib/postgresql/data

  fwo-app:
    image: cactusecurity/firewall-orchestrator:latest
    depends_on:
      - db
    environment:
      DB_HOST: db
      DB_NAME: fwo
      DB_USER: fwo
      DB_PASSWORD: fwo_secure_password
    ports:
      - "8080:8080"
    volumes:
      - ./imports:/app/imports
      - ./exports:/app/exports

volumes:
  pgdata:
```

## Comparison Table

| Feature | Capirca | Aerleon | Firewall Orchestrator |
|---------|---------|---------|----------------------|
| **Approach** | Policy-to-config generation | Policy-to-config generation | Rule import and analysis |
| **GitHub Stars** | 852 | 244 | 54 |
| **Vendor Support** | 20+ platforms | 20+ platforms | 10+ importers |
| **Policy Language** | Custom DSL and YAML | YAML-first | Import-based |
| **Web UI** | No | No | Yes (Django) |
| **Compliance** | Manual audit | Manual audit | Built-in checks |
| **Change Management** | Git-based | Git-based | Workflow engine |
| **Docker Support** | Custom image | Python base image | Official image |
| **Best For** | Google-scale ACL generation | New deployments, YAML fans | Rule auditing and compliance |

## Choosing the Right Tool

**Use Capirca if:** You have existing Capirca policy files, need the widest vendor coverage, or are operating at Google-scale ACL management. Capirca is battle-tested in production environments managing thousands of rules.

**Use Aerleon if:** You are starting a new firewall policy management project. Its YAML-first approach is more intuitive, the plugin system is more extensible, and it benefits from active maintenance and regular updates. Aerleon is the forward-looking choice.

**Use Firewall Orchestrator if:** Your primary need is auditing and compliance rather than policy generation. If you need to import existing rules from multiple vendors, analyze them for redundancies and violations, and manage change workflows through a web interface, Firewall Orchestrator is the right fit.

For many organizations, the ideal setup combines Aerleon (for policy generation) with Firewall Orchestrator (for auditing and compliance) — generate configs with Aerleon, deploy them, then import and audit the live rules with Firewall Orchestrator.

For related network security reading, see our [WAF comparison guide](../2026-04-18-bunkerweb-vs-modsecurity-vs-crowdsec-self-hosted-waf-guide-2026/) and [API firewall analysis](../2026-04-26-krakend-vs-coraza-vs-envoy-self-hosted-api-firewall-guide/).

## Why Self-Host Firewall Policy Management?

Managing firewall rules through vendor-specific interfaces creates several problems that self-hosted policy management tools solve:

**Data ownership and control.** Firewall rules define your network security posture. Storing policy definitions in your own infrastructure — rather than relying on cloud-based management platforms — ensures you maintain full control over your security configurations. Self-hosted tools keep your network topology, IP addressing, and security policies within your perimeter.

**Cost savings at scale.** Commercial firewall management platforms (Tufin, AlgoSec, FireMon) charge per-managed-device pricing that scales linearly with infrastructure size. For organizations managing dozens of firewalls across multiple sites, open-source alternatives provide comparable capabilities without per-device licensing fees. The total cost of ownership for Capirca or Aerleon is essentially the infrastructure cost to run the policy generation pipeline.

**No vendor lock-in.** Vendor-specific management tools create deep dependencies. When you define firewall policies in a vendor-neutral format, you can migrate between firewall vendors without rewriting your entire policy base. This is especially valuable when consolidating acquisitions, changing cloud providers, or modernizing legacy network equipment.

**Automated compliance.** Self-hosted policy management tools can be integrated into CI/CD pipelines, enabling automated compliance checks before any rule reaches production. Every policy change is version-controlled, reviewed, and tested — eliminating the manual spreadsheet-and-email workflows that lead to security gaps.

**Multi-cloud and hybrid consistency.** Organizations running infrastructure across AWS, GCP, Azure, and on-premises data centers need a unified policy layer. Capirca and Aerleon generate security groups for cloud providers alongside traditional firewall configs, ensuring consistent security posture across your entire estate.

For infrastructure-as-code practices, see our [drift detection guide](../self-hosted-infrastructure-drift-detection-driftctl-cloud-custodian-opentofu-gui/) and [policy-as-code tools comparison](../2026-05-09-policy-as-code-tools-opa-conftest-gatekeeper-guide/).

## FAQ

### What is the difference between Capirca and Aerleon?

Aerleon is a fork and successor to the Capirca project. Both generate vendor-specific firewall configurations from abstract policy definitions. The key differences are: Aerleon uses YAML as its primary policy format (Capirca uses a custom DSL), has a more extensible plugin architecture, better error messages, and more active maintenance. Aerleon can also read existing Capirca policy files, making migration straightforward.

### Can Firewall Orchestrator generate firewall rules from scratch?

No. Firewall Orchestrator primary function is importing and analyzing existing firewall rules from multiple vendors. It normalizes rules into a common format for auditing, compliance checking, and change management. For rule generation from abstract policies, use Capirca or Aerleon instead. The tools complement each other — generate with Aerleon, audit with Firewall Orchestrator.

### How many firewall platforms does Capirca support?

Capirca supports 20+ platforms including Cisco ASA, Cisco XR, Juniper SRX, Juniper MSMPC, Palo Alto Networks, iptables, nftables, Arista EOS, AWS Security Groups, GCP Firewall Rules, Azure NSG, PCAP (for testing), and Windows Firewall. The full list is available in the Capirca documentation under the lib directory.

### Is Aerleon production-ready?

Yes. Aerleon is used in production by multiple organizations and has an active development community. It is backwards compatible with Capirca policy files, so you can migrate incrementally. The project has comprehensive test suites, CI/CD pipelines, and regular releases. For new deployments, Aerleon is the recommended choice over Capirca.

### How do I integrate these tools into CI/CD pipelines?

For Capirca and Aerleon, the typical pattern is: store policy files in Git, run policy validation as a pre-merge check, generate vendor configs on merge to main, and deploy configs via your configuration management tool (Ansible, Terraform). Aerleon provides pre-built GitHub Actions workflows. For Firewall Orchestrator, schedule periodic imports from live firewalls and run compliance reports on a cron schedule.

### What happens when a firewall vendor changes its configuration syntax?

Capirca and Aerleon abstract vendor syntax behind output generator plugins. When a vendor updates its CLI or API, you update the corresponding plugin — your policy definitions remain unchanged. This is a key advantage over manual configuration: the abstraction layer shields you from vendor-specific syntax changes.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Firewall Policy Management: Capirca vs Aerleon vs Firewall Orchestrator (2026)",
  "description": "Compare open-source firewall policy management tools: Capirca, Aerleon, and Firewall Orchestrator. Learn which tool fits your network security workflow.",
  "datePublished": "2026-05-14",
  "dateModified": "2026-05-14",
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
