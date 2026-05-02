---
title: "Self-Hosted LIMS: Bika LIMS vs SENAITE vs iskylims for Laboratory Management (2026)"
date: 2026-05-02
tags: ["comparison", "guide", "self-hosted", "laboratory", "data-management"]
draft: false
---

A Laboratory Information Management System (LIMS) tracks samples, test results, instruments, and workflows in research and quality control labs. While commercial LIMS solutions cost thousands per year, open-source alternatives provide full functionality with self-hosted deployment options. This guide compares the leading self-hosted LIMS platforms.

## What Is a LIMS?

A LIMS manages the complete lifecycle of laboratory samples and analyses:

- **Sample tracking** — barcode-based chain of custody from intake to disposal
- **Workflow management** — configurable test sequences and approval processes
- **Result management** — automated calculation, validation, and reporting
- **Instrument integration** — direct connection to analytical instruments
- **Quality control** — control charts, proficiency testing, and audit trails
- **Regulatory compliance** — 21 CFR Part 11, ISO 17025, and GLP support

## Bika LIMS

[Bika LIMS](https://www.bikalabs.com/) is built on the Plone CMS and provides a comprehensive laboratory management system. It is the foundation for several specialized LIMS implementations and has been in development for over a decade.

### Key Features

- **Plone-based architecture** — leverages Plone''s workflow engine and content management
- **Configurable workflows** — define sample lifecycle stages with role-based transitions
- **Sample management** — full chain of custody with barcode support
- **Analysis management** — define test methods, calculation formulas, and result validation
- **Reporting** — PDF report generation with customizable templates
- **Multi-site support** — manage multiple laboratories from a single instance

### Docker Compose Deployment

```yaml
version: '3.8'

services:
  bikalims:
    image: plone/plone:latest
    ports:
      - "8080:8080"
    environment:
      - PLONE_ADDONS=bika.lims
      - PLONE_ZCML=bika.lims
      - POSTGRES_USER=plone
      - POSTGRES_PASSWORD=plone
      - POSTGRES_HOST=postgres
    depends_on:
      - postgres
    volumes:
      - bikalims_data:/data
    networks:
      - lims-net

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=plone
      - POSTGRES_PASSWORD=plone
      - POSTGRES_DB=plone
    volumes:
      - pg_data:/var/lib/postgresql/data
    networks:
      - lims-net

networks:
  lims-net:
    driver: bridge

volumes:
  bikalims_data:
  pg_data:
```

### Pros and Cons

| Feature | Details |
|---------|---------|
| Pros | Mature platform, Plone workflow engine, highly configurable, regulatory compliance support |
| Cons | Plone learning curve, complex setup, slower performance with large datasets |
| GitHub | Active on Plone ecosystem |
| Best for | Quality control labs, environmental testing, regulatory compliance |

## SENAITE

[SENAITE](https://www.senaite.org/) is a fork of Bika LIMS, re-architected with a modern UI and streamlined workflows. It focuses on usability and is designed for laboratories that need a simpler, faster setup than Bika LIMS provides.

### Key Features

- **Modern UI** — Bootstrap-based responsive interface
- **Simplified workflows** — pre-configured sample and analysis workflows
- **Instrument integration** — direct import from laboratory instruments
- **Client portal** — web-based access for clients to view results
- **Multi-language** — internationalized interface
- **Active community** — dedicated forum and documentation

### Docker Compose Deployment

```yaml
version: '3.8'

services:
  senaite:
    image: senaite/senaite:latest
    ports:
      - "8080:8080"
    environment:
      - POSTGRES_USER=senaite
      - POSTGRES_PASSWORD=senaite
      - POSTGRES_HOST=postgres
    depends_on:
      - postgres
    volumes:
      - senaite_data:/data
    networks:
      - lims-net

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=senaite
      - POSTGRES_PASSWORD=senaite
      - POSTGRES_DB=senaite
    volumes:
      - pg_data:/var/lib/postgresql/data
    networks:
      - lims-net

networks:
  lims-net:
    driver: bridge

volumes:
  senaite_data:
  pg_data:
```

### Pros and Cons

| Feature | Details |
|---------|---------|
| Pros | Modern interface, simpler setup than Bika, active community, good documentation |
| Cons | Smaller feature set than Bika, limited customization options |
| GitHub | Active development |
| Best for | Clinical labs, research labs, small-to-medium testing facilities |

## iskylims

[iskylims](https://github.com/BU-ISCIII/iskylims) is an open-source LIMS developed at the ISCIII Bioinformatics Unit, specifically designed for Next Generation Sequencing (NGS) sample management and bioinformatics analysis workflow tracking.

### Key Features

- **NGS-focused** — tailored for sequencing laboratory workflows
- **Sample tracking** — from DNA extraction through library preparation to sequencing
- **Analysis management** — track bioinformatics pipeline execution and results
- **Reporting** — generate summary reports for sequencing runs
- **Statistics** — built-in statistics and quality metrics
- **Lightweight** — Django-based, easier to deploy than Plone-based alternatives

### Docker Compose Deployment

```yaml
version: '3.8'

services:
  iskylims:
    image: ghcr.io/bu-isciii/iskylims:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgres://iskylims:iskylims@postgres:5432/iskylims
      - SECRET_KEY=your-secret-key-change-in-production
    depends_on:
      - postgres
    volumes:
      - iskylims_data:/app/data
    networks:
      - lims-net

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=iskylims
      - POSTGRES_PASSWORD=iskylims
      - POSTGRES_DB=iskylims
    volumes:
      - pg_data:/var/lib/postgresql/data
    networks:
      - lims-net

networks:
  lims-net:
    driver: bridge

volumes:
  iskylims_data:
  pg_data:
```

### Pros and Cons

| Feature | Details |
|---------|---------|
| Pros | NGS-specialized, Django-based (easier deployment), statistics built-in, 91 GitHub stars |
| Cons | Niche focus, smaller community, less configurable for non-NGS labs |
| GitHub Stars | 91 |
| Best for | Bioinformatics labs, NGS facilities, research institutions |

## Comparison Table

| Feature | Bika LIMS | SENAITE | iskylims |
|---------|-----------|---------|----------|
| Base framework | Plone | Plone (fork) | Django |
| Primary focus | General laboratory | General laboratory | NGS / Bioinformatics |
| Sample tracking | Full chain of custody | Full chain of custody | NGS workflow tracking |
| Workflow engine | Plone workflow | Pre-configured | Django admin |
| UI | Plone Classic | Bootstrap modern | Django admin |
| Regulatory compliance | 21 CFR Part 11, ISO 17025 | ISO 17025 support | Basic audit trail |
| Client portal | Yes | Yes | No |
| Instrument integration | Yes | Yes | Limited |
| Multi-language | Yes | Yes | Partial |
| Database | PostgreSQL | PostgreSQL | PostgreSQL |
| Docker support | Community images | Community images | GHCR image |
| Community size | Large | Medium | Small |
| Learning curve | Steep | Moderate | Low |
| Best for | QC labs, regulated environments | General lab management | NGS / sequencing labs |

## Why Self-Host Your LIMS?

Laboratory data is among the most sensitive in any organization — it includes proprietary research results, patient information, and quality control data that directly impacts regulatory compliance.

**Regulatory compliance**: Self-hosting ensures you maintain complete control over data residency, access logs, and audit trails required by 21 CFR Part 11, ISO 17025, and GLP regulations. Cloud-hosted LIMS may not meet all jurisdictional requirements.

**Customization**: Every laboratory has unique workflows. Open-source LIMS platforms can be modified to match your exact sample intake process, approval chains, and reporting formats — something commercial SaaS products rarely allow.

**Integration with instruments**: Self-hosted LIMS can connect directly to laboratory instruments on your local network without requiring cloud gateways or VPN tunnels. This reduces latency for real-time instrument monitoring and eliminates network dependency for critical lab operations.

**Cost**: Commercial LIMS licenses range from $5,000 to $50,000+ per year. Self-hosted open-source alternatives eliminate licensing costs, leaving only infrastructure expenses.

For related infrastructure, see our [self-hosted document signing guide](../2026-04-24-docuseal-vs-opensign-vs-libresign-self-hosted-document-signing-guide/) for lab report approval workflows, and our [email archiving guide](../2026-04-18-self-hosted-email-archiving-mailpiler-dovecot-stalwart-guide-2026/) for preserving laboratory correspondence.

## FAQ

### What is the difference between Bika LIMS and SENAITE?

SENAITE is a fork of Bika LIMS with a modernized user interface and simplified workflows. Bika LIMS offers more configuration options and regulatory compliance features, while SENAITE prioritizes ease of use and faster setup. Both use Plone as their underlying framework.

### Can iskylims be used for non-NGS laboratories?

iskylims is specifically designed for NGS sample management and bioinformatics workflows. While its core sample tracking features could be adapted, laboratories needing general LIMS functionality should consider Bika LIMS or SENAITE instead.

### Do self-hosted LIMS platforms support regulatory compliance?

Bika LIMS has the strongest regulatory compliance support, including 21 CFR Part 11 electronic signatures and ISO 17025 workflow requirements. SENAITE supports ISO 17025. iskylims provides basic audit trail functionality suitable for research environments.

### How much storage does a self-hosted LIMS need?

For a small laboratory processing 50-100 samples per week, plan for 50-100 GB of PostgreSQL storage for sample records and results. Additional storage is needed for instrument data files, PDF reports, and backup archives. Plan for 500 GB to 1 TB for the first year of operation.

### Can a LIMS integrate with laboratory instruments?

Bika LIMS and SENAITE both support instrument integration through configurable import parsers for CSV, XML, and proprietary instrument output formats. Some instruments require custom adapters, which can be developed using the platform''s extension framework.

### Is Plone a good foundation for a LIMS?

Plone provides excellent workflow management, content versioning, and access control — all critical for laboratory operations. However, it has a steeper learning curve than Django or Rails-based alternatives. The trade-off is a more robust workflow engine out of the box.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted LIMS: Bika LIMS vs SENAITE vs iskylims for Laboratory Management (2026)",
  "description": "Compare self-hosted Laboratory Information Management Systems: Bika LIMS, SENAITE, and iskylims. Docker Compose configs, feature comparison, and deployment guides.",
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
