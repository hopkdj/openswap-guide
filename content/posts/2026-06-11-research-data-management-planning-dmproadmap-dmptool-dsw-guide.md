---
title: "Self-Hosted Research Data Management Planning: DMPRoadmap vs DMPTool vs Data Stewardship Wizard"
date: "2026-06-11"
tags: ["research-data-management", "dmp", "data-management-plan", "open-science", "research-infrastructure", "dmproadmap", "dmptool", "self-hosted", "academic-software", "fair-data"]
draft: false
---

## Introduction

Research Data Management (RDM) has become a mandatory requirement for publicly funded research worldwide. Funding agencies from the National Science Foundation to the European Commission now require researchers to submit **Data Management Plans (DMPs)** as part of grant applications — documents that describe how research data will be collected, stored, preserved, and shared. For university research offices and libraries, managing hundreds of DMPs across diverse disciplines requires dedicated software platforms.

This article compares three leading open-source DMP platforms that research institutions can self-host: **DMPRoadmap** (the upstream project from the Digital Curation Centre), **DMPTool** (the UC3-hosted US implementation), and **Data Stewardship Wizard (DSW)** (a collaborative knowledge-modeling approach from ELIXIR). Each platform takes a fundamentally different approach to guiding researchers through the complex landscape of data management planning.

## Comparison Table

| Feature | DMPRoadmap | DMPTool | Data Stewardship Wizard (DSW) |
|---------|-----------|---------|-------------------------------|
| **Primary Role** | Collaborative DMP authoring platform | US-focused DMPRoadmap instance | Knowledge-model-driven DMP creation |
| **GitHub Stars** | 118+ | 67+ | 21+ |
| **Language** | Ruby on Rails | Ruby on Rails (fork) | Haskell + Elm + Python |
| **Maintainer** | DCC (UK) + UC3 (US) | UC3 / California Digital Library | ELIXIR CZ / DSW Community |
| **Docker Support** | Yes (docker-compose) | Yes (docker-compose) | Yes (docker-compose) |
| **Template System** | Funder-specific templates | US funder templates (NSF, NIH, etc.) | Knowledge models (customizable) |
| **Multi-Institutional** | Yes (multi-tenant) | Yes (multi-tenant) | Yes (multi-tenant) |
| **API Access** | REST API (v2) | REST API (v2) | REST API + GraphQL |
| **Machine-Actionable DMP** | RDA Common Standard support | RDA Common Standard support | Built-in maDMP export |
| **Question Guidance** | Static guidance text | Static guidance text | Dynamic, context-aware guidance |
| **Integration Ecosystem** | ORCID, Shibboleth, SAML | ORCID, Shibboleth, InCommon | ORCID, OIDC, SAML |
| **Production Deployments** | 30+ institutions (mostly EU/UK) | 300+ US institutions | 20+ institutions (mostly EU) |

## DMPRoadmap: The Collaborative Foundation

DMPRoadmap is the upstream open-source project jointly developed by the Digital Curation Centre (DCC) in the UK and the California Digital Library (CDL/UC3) in the US. It provides a multi-tenant platform where research institutions can create branded DMP services with funder-specific templates, institutional guidance, and collaborative editing features.

### Key Features

- **Funder-Aware Templates**: Automatically loads the correct DMP template based on the selected funding agency, with institutional guidance overlaid
- **Collaborative Authoring**: Multiple researchers can co-author a DMP simultaneously with role-based access control
- **Multi-Phase Planning**: Supports initial, detailed, and final DMP versions aligned with grant lifecycle stages
- **ORCID Integration**: Auto-populates researcher profiles and publication lists via ORCID API
- **Institutional Branding**: Each tenant organization gets a fully branded interface with custom logos, colors, and domain

### Docker Deployment

```yaml
version: "3.8"
services:
  dmproadmap-web:
    image: dmproadmap/dmp-roadmap:latest
    container_name: dmp-web
    ports:
      - "3000:3000"
    environment:
      - RAILS_ENV=production
      - DATABASE_URL=mysql2://dmpuser:dmppass@mysql:3306/dmp_production
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY_BASE=your-secret-key-here
      - DEVISE_SECRET_KEY=your-devise-key
      - WICKED_PDF_PATH=/usr/local/bin/wkhtmltopdf
    depends_on:
      - mysql
      - redis
    volumes:
      - dmp-uploads:/app/public/uploads
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    container_name: dmp-mysql
    environment:
      - MYSQL_ROOT_PASSWORD=rootpass
      - MYSQL_DATABASE=dmp_production
      - MYSQL_USER=dmpuser
      - MYSQL_PASSWORD=dmppass
    volumes:
      - mysql-data:/var/lib/mysql
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: dmp-redis
    volumes:
      - redis-data:/data
    restart: unless-stopped

volumes:
  dmp-uploads:
  mysql-data:
  redis-data:
```

### Configuration

```bash
# Initialize database
docker exec dmp-web rails db:create db:migrate db:seed

# Create admin user
docker exec dmp-web rails users:create_admin

# Load funder templates
docker exec dmp-web rails templates:load_all

# Configure institution
docker exec dmp-web rails orgs:create name="University of Example" \
  abbreviation="UoE" target_url="https://dmp.example.edu"
```

## DMPTool: The US Deployment Powerhouse

DMPTool is the production deployment of DMPRoadmap operated by the University of California Curation Center (UC3). While it shares the same core codebase as DMPRoadmap, DMPTool includes US-specific customizations, funder integrations, and serves over 300 US research institutions with a shared tenant model.

### Key Features

- **US Funder Library**: Pre-built templates for NSF, NIH, DOE, DOD, USDA, NASA, NEH, and dozens of other US funding agencies
- **Single Sign-On**: Integration with InCommon Federation, enabling researchers from any US university to log in with their institutional credentials
- **Institutional Dashboard**: Administrators can review, comment on, and approve DMPs within their institution
- **Proven Scale**: Over 100,000 DMPs created by researchers across 300+ US institutions
- **Continuous Updates**: Templates updated as funding agencies revise their DMP requirements

### Customization for Self-Hosting

```bash
# Clone the DMPTool repository (forked from DMPRoadmap)
git clone https://github.com/CDLUC3/dmptool.git
cd dmptool

# Configure US-specific settings
echo "DMPTool::Application.configure do
  config.x.dmproadmap.brand_name = 'My Institution DMP Tool'
  config.x.dmproadmap.funder_registry_url = 'https://doi.org/10.13039'
  config.x.dmproadmap.shibboleth_enabled = true
end" > config/initializers/dmptool_custom.rb

# Deploy with the same Docker Compose setup
docker-compose up -d
```

## Data Stewardship Wizard: The Knowledge-Model Approach

Data Stewardship Wizard (DSW) takes a fundamentally different approach to DMP creation. Instead of static templates with guidance text, DSW uses **knowledge models** — structured representations of data management expertise that dynamically adapt questions based on previous answers. This means a researcher in genomics sees different questions than a researcher in computational social science, each receiving domain-specific guidance.

### Key Features

- **Knowledge Models**: Expert-crafted question trees that encode domain-specific data management best practices
- **Dynamic Questionnaires**: Questions adapt based on previous answers — no irrelevant questions shown
- **Machine-Actionable DMPs**: Native export to the RDA maDMP standard (JSON-LD format) for machine processing
- **Document Generation**: Export DMPs as PDF, DOCX, LaTeX, or HTML with customizable templates
- **Project Phases**: Track DMPs across Before, During, and After project phases with distinct guidance per phase
- **Metrics & FAIR Assessment**: Built-in tools to evaluate how well your DMP addresses FAIR principles

### Docker Deployment

```yaml
version: "3.8"
services:
  dsw-server:
    image: datastewardshipwizard/dsw-server:latest
    container_name: dsw-server
    ports:
      - "3000:3000"
    environment:
      - DSW_DB_HOST=postgres
      - DSW_DB_PORT=5432
      - DSW_DB_NAME=dsw
      - DSW_DB_USER=dswuser
      - DSW_DB_PASSWORD=dswpass
      - DSW_S3_ENDPOINT=http://minio:9000
      - DSW_S3_BUCKET=dsw-documents
      - DSW_S3_ACCESS_KEY=minioadmin
      - DSW_S3_SECRET_KEY=minioadmin
    depends_on:
      - postgres
      - minio
    restart: unless-stopped

  dsw-client:
    image: datastewardshipwizard/dsw-client:latest
    container_name: dsw-client
    ports:
      - "8080:80"
    environment:
      - DSW_API_URL=http://dsw-server:3000
    depends_on:
      - dsw-server
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    container_name: dsw-postgres
    environment:
      - POSTGRES_DB=dsw
      - POSTGRES_USER=dswuser
      - POSTGRES_PASSWORD=dswpass
    volumes:
      - pg-data:/var/lib/postgresql/data
    restart: unless-stopped

  minio:
    image: minio/minio:latest
    container_name: dsw-minio
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    volumes:
      - minio-data:/data
    restart: unless-stopped

volumes:
  pg-data:
  minio-data:
```

### Creating Knowledge Models

```python
# Example: Defining a knowledge model fragment (simplified)
knowledge_model = {
    "uuid": "d3f4a5b6-c789-0123-4567-89abcdef0123",
    "chapters": [{
        "title": "Data Collection",
        "questions": [{
            "uuid": "q1",
            "text": "What type of data will you collect?",
            "type": "multi-choice",
            "answers": [
                {"text": "Experimental measurements", "follow_up": "q1a"},
                {"text": "Survey responses", "follow_up": "q1b"},
                {"text": "Computational simulations", "follow_up": "q1c"}
            ],
            "guidance": "Select the primary method of data generation."
        }]
    }]
}
```

## Machine-Actionable DMPs and the RDA Standard

The Research Data Alliance (RDA) DMP Common Standards Working Group has developed a standardized JSON-based format for Data Management Plans known as **maDMP (Machine-Actionable DMP)**. This standard (93+ stars on GitHub) enables DMPs to be processed, validated, and shared programmatically across different platforms and institutions.

All three platforms support maDMP export to varying degrees. DSW has the most comprehensive native support, DMPRoadmap and DMPTool support it through the RDA Common Standard integration, and all three are actively participating in the RDA working group to improve interoperability.

## Choosing the Right DMP Platform

**Choose DMPRoadmap if:**
- You are a European or international research institution wanting the upstream codebase
- You need a proven, widely-adopted platform with a large community
- You want maximum flexibility in customization and branding
- You plan to contribute improvements back to the open-source community

**Choose DMPTool if:**
- You are a US-based research institution
- You need pre-built templates for US federal funding agencies (NSF, NIH, DOE, etc.)
- You want InCommon Federation integration for seamless institutional SSO
- You prefer a hosted solution with the option to self-host

**Choose Data Stewardship Wizard if:**
- You want intelligent, context-aware guidance rather than static templates
- Machine-actionable DMPs are a priority for your institution
- You want sophisticated document generation with LaTeX/PDF/DOCX export
- You are willing to invest in building custom knowledge models for your research domains

## Why Self-Host Your DMP Platform?

The data management planning landscape is increasingly regulatory. The 2022 Nelson Memo from the White House Office of Science and Technology Policy mandates that all federally funded research data be made publicly accessible by 2025, and the European Open Science Cloud (EOSC) is driving similar requirements across EU member states. Self-hosting your DMP platform ensures that your institution maintains control over sensitive research proposals — many DMPs contain preliminary data, novel methodologies, and grant strategy details that researchers prefer not to share with third-party cloud providers.

Furthermore, self-hosting allows you to deeply integrate DMP workflows with your existing research information management systems. For example, you can connect your DMP platform to our [research analytics platforms](../2026-06-11-research-analytics-platforms-openalex-lens-vivo/) to automatically populate publication lists, or link to your institutional repository for automated data deposit workflows. Our [digital archive platforms guide](../2026-04-23-archivematica-vs-omeka-s-vs-dspace-self-hosted-digital-arch/) covers long-term preservation solutions that complement DMP platforms, while our [library digital collection systems guide](../2026-05-02-koha-vs-omeka-vs-invenio-self-hosted-library-digital-collec/) addresses the broader research output management ecosystem.

**FAIR compliance**: Self-hosted DMP tools help your institution meet FAIR (Findable, Accessible, Interoperable, Reusable) data principles by embedding FAIR assessment directly into the planning process. Rather than retroactively checking compliance, researchers receive FAIR guidance as they write their DMP, increasing the likelihood that funded research produces truly reusable data. The maDMP standard further enables automated validation of FAIR compliance across your entire portfolio of funded projects.

## Deployment Best Practices

**Authentication Integration**: All three platforms support SAML, OIDC, and Shibboleth for institutional single sign-on. Configure your identity provider to enable one-click access for researchers. For ORCID integration, register your platform as an ORCID client to enable automatic profile and publication syncing.

**Template Management**: Designate a data librarian or research data management specialist as the template curator. Funders update DMP requirements every 1-3 years, and templates need corresponding updates. DMPRoadmap and DMPTool can auto-load templates from the DCC registry, but institutional guidance overlays require manual maintenance.

**Backup and Disaster Recovery**: DMPs are often the only documentation of how valuable research data should be managed. Ensure your database and document storage (S3/minio) are backed up regularly. Consider geographic redundancy if your institution spans multiple campuses.

## FAQ

### What is the difference between a DMP and a data repository?

A Data Management Plan (DMP) is a planning document that describes how data will be managed during and after a research project. A data repository is where the actual data is stored and shared. DMP platforms help you plan the data lifecycle; repositories execute the storage and sharing plan. They are complementary tools in the research data management ecosystem.

### Can DMP platforms integrate with grant management systems?

Yes. All three platforms provide REST APIs that allow integration with grant management systems, research information systems (CRIS), and electronic research administration (eRA) platforms. DMPTool and DMPRoadmap support the RDA Common Standard for machine-actionable DMPs, enabling automated DMP submission as part of grant application workflows.

### Do these platforms support non-English languages?

DMPRoadmap and DMPTool include internationalization (i18n) support with community-contributed translations for Spanish, French, German, Portuguese, and several other languages. DSW uses knowledge models that can be authored in any language, with the interface available in English and community translations for Czech, German, and Dutch expanding.

### How do machine-actionable DMPs help researchers?

Machine-actionable DMPs (maDMPs) use the RDA Common Standard JSON-LD format, enabling automated processing by grant management systems, repository platforms, and compliance checkers. For researchers, this means fewer manual data entry steps: their DMP can automatically trigger repository space allocation, configure data storage quotas, and pre-populate metadata schemas, reducing the administrative burden of research data management.

### Is DSW harder to set up than DMPRoadmap?

DSW requires more initial investment in knowledge model configuration, as its strength comes from customized question trees per research domain. However, its Docker deployment is just as straightforward as DMPRoadmap. For institutions without dedicated RDM expertise, DMPRoadmap provides a quicker path to production with its pre-built funder templates, while DSW offers more sophisticated guidance for institutions with mature RDM programs.

### Can researchers from multiple institutions collaborate on the same DMP?

Yes. All three platforms support cross-institutional collaboration with role-based access control. You can invite co-PIs from other universities as collaborators on your DMP, each using their own institutional credentials (via federated authentication). This is particularly valuable for multi-institutional grant proposals where data management responsibilities are shared.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Research Data Management Planning: DMPRoadmap vs DMPTool vs Data Stewardship Wizard",
  "description": "In-depth comparison of three open-source Data Management Planning platforms for research institutions: DMPRoadmap, DMPTool, and Data Stewardship Wizard. Includes Docker deployment, machine-actionable DMP integration, and FAIR data compliance guidance.",
  "datePublished": "2026-06-11",
  "dateModified": "2026-06-11",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
