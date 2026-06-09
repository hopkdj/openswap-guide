---
title: "Self-Hosted Virtual Research Environments: VIVO vs CyVerse Atmosphere vs HubZero Compared"
date: "2026-06-10"
tags: ["research-collaboration", "virtual-research", "science-gateway", "open-science", "research-networking", "self-hosted", "docker"]
draft: false
---

Modern scientific research is inherently collaborative, often spanning multiple institutions, disciplines, and geographic regions. Virtual Research Environments (VREs) — also called science gateways or collaboratories — provide web-based platforms where researchers can discover collaborators, share data and tools, run computational analyses, and manage projects in a unified digital workspace. Unlike general-purpose collaboration tools like wikis or shared drives, VREs are purpose-built for research workflows: they understand research profiles, grant management, publication tracking, and scientific data sharing. Three open-source platforms lead this space: **VIVO** for research networking and expertise discovery, **CyVerse Atmosphere** for cloud-based computational research, and **HubZero** for building custom science gateway websites.

## Understanding Virtual Research Environments

A Virtual Research Environment bridges the gap between generic infrastructure (servers, storage, networks) and the specific needs of research communities. Rather than requiring every research group to build their own web portal, data catalog, and collaboration tools from scratch, VREs provide modular platforms that can be configured for specific scientific domains — whether it's genomics, climate science, materials engineering, or social science surveys.

The core capabilities of a VRE include: researcher profiles and expertise discovery (who works on what), project workspaces with shared data and tools, computational resource provisioning (launching analysis environments on institutional clusters or cloud), publication and grant tracking, and integration with domain-specific data repositories and analysis tools.

## Comparison Table: VIVO vs CyVerse Atmosphere vs HubZero

| Feature | VIVO (vivo-project/VIVO) | CyVerse Atmosphere | HubZero (HUBzero) |
|---------|--------------------------|-------------------|-------------------|
| **Developer** | VIVO Project (Lyrasis) | University of Arizona / CyVerse | HUBzero Foundation (Purdue) |
| **GitHub Stars** | 234 | 347 | 47 |
| **Primary Language** | Java | Python | PHP |
| **Primary Focus** | Research networking & expertise discovery | Cloud-based scientific computing | Science gateway / portal builder |
| **Core Features** | Researcher profiles, publication tracking, grant mapping, co-author networks | VM/image provisioning, data store, interactive apps, scalable compute | CMS for research, simulation tools, data management, publishing |
| **User Management** | Shibboleth/LDAP/SAML SSO | CyVerse accounts, LDAP, OAuth | Joomla user system, LDAP, CAS |
| **Semantic Web** | Yes (RDF/OWL, linked data) | No | No |
| **Data Management** | External (linked data) | Integrated Data Store (iRODS) | Project workspaces, DataStore |
| **Compute Resources** | None (profiles only) | Cloud VMs, HPC, containers | Simulation tools, HPC integration |
| **Publication Integration** | CrossRef, PubMed, ORCID | DOI minting, DataCite | Built-in publication workflow |
| **Deployment** | Docker, Tomcat, Solr | OpenStack-based cloud | LAMP stack (Joomla-based) |
| **License** | Apache 2.0 | BSD-3 | GNU GPL v2 |

## Deploying VIVO with Docker Compose

VIVO provides an official Docker Compose configuration that bundles the application with Solr search and a MySQL/MariaDB database. This is the recommended deployment method:

```yaml
version: '3'
services:
  vivo:
    image: vivopub/vivo:latest
    container_name: vivo
    environment:
      - CATALINA_OPTS=-Xmx4g -Xms1g
      - VIVO_DB_HOST=mysql
      - VIVO_DB_NAME=vivo
      - VIVO_DB_USER=vivo
      - VIVO_DB_PASSWORD=securepassword
      - VIVO_SOLR_URL=http://solr:8983/solr/vivo
    ports:
      - "8080:8080"
    volumes:
      - ./vivo/home:/usr/local/vivo/home
      - ./vivo/uploads:/usr/local/vivo/uploads
    depends_on:
      - mysql
      - solr

  mysql:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=rootpassword
      - MYSQL_DATABASE=vivo
      - MYSQL_USER=vivo
      - MYSQL_PASSWORD=securepassword
    volumes:
      - mysql_data:/var/lib/mysql

  solr:
    image: solr:8
    command: solr-create -c vivo
    volumes:
      - solr_data:/var/solr

volumes:
  mysql_data:
  solr_data:
```

VIVO uses semantic web technologies (RDF, OWL) to model researcher profiles, publications, grants, and organizational structures as linked data. This enables powerful cross-institutional queries — for example, finding all researchers working on "machine learning for climate modeling" who have NIH funding and have published in the last two years.

## Deploying CyVerse Atmosphere

CyVerse Atmosphere provides a cloud management platform for scientific computing. It orchestrates virtual machines on OpenStack, giving researchers self-service access to pre-configured analysis environments. The deployment is more complex and typically requires an OpenStack cloud:

```bash
# Core Atmosphere services
git clone https://github.com/cyverse/atmosphere.git
cd atmosphere

# Configure for your OpenStack deployment
cp variables.ini.dist variables.ini

docker compose up -d
```

Atmosphere provides a web-based dashboard where researchers can browse a catalog of pre-built images (RStudio Server, Jupyter, QIIME, MATLAB) and launch them as virtual machines with a few clicks. The platform handles authentication, resource quotas, image management, and instance lifecycle — researchers never need to know the underlying cloud infrastructure exists.

## Deploying HubZero

HubZero is built on the Joomla CMS framework but adds specialized components for research: simulation tools, data management, publication workflows, and collaboration spaces. It powers over 100 science gateways including nanoHUB.org (nanotechnology simulations) and pharmaHUB.org:

```bash
# HubZero requires a LAMP stack
docker run -d \
  --name hubzero \
  -p 80:80 \
  -v /srv/hubzero:/var/www/hubzero \
  -e MYSQL_HOST=mysql \
  -e MYSQL_DATABASE=hubzero \
  -e MYSQL_USER=hubzero \
  -e MYSQL_PASSWORD=securepassword \
  hubzero/hubzero:latest
```

HubZero's standout feature is its simulation tool framework — researchers can publish computational models as interactive web tools with parameter forms, visualization outputs, and job submission to HPC clusters. This turns research software that previously required command-line expertise into accessible web applications.

## Why Self-Host Your Virtual Research Environment?

Self-hosting a VRE gives your institution control over researcher data, compliance with privacy regulations (GDPR, HIPAA for clinical research), and integration with existing identity management systems. When you deploy VIVO, you control exactly what profile information is public, who can search your researcher database, and how publication data is linked to internal grant management systems. CyVerse Atmosphere self-hosted on your own OpenStack cluster keeps sensitive research data and computational workflows entirely within your network perimeter.

The strategic advantage extends beyond compliance. A self-hosted VRE becomes part of your institution's research infrastructure portfolio — it integrates with your HPC scheduler, your storage systems, and your single sign-on. It can be customized with your institution's branding, domain-specific tools, and workflows that reflect how your researchers actually work, rather than adapting to a one-size-fits-all hosted service.

For managing research outputs and publications, see our [scholarly publishing platforms guide](../2026-06-04-scholarly-publishing-platforms-ojs-janeway-lodel-guide/). If you need preprint and open access repositories, our [preprint repository comparison](../2026-06-09-self-hosted-preprint-repositories-osf-ops-eprints/) covers OSF, OPS, and EPrints. For team knowledge management, check our [knowledge base platforms guide](../2026-04-24-docmost-vs-outline-vs-affine-self-hosted-knowledge-base-guide-2026/).

## Integrating VREs with Institutional Research Information Systems

A Virtual Research Environment is most valuable when it connects to existing institutional systems rather than operating as an isolated silo. VIVO's semantic web architecture makes it the natural integration hub — its RDF data model can ingest publication data from institutional repositories via OAI-PMH, pull grant information from research management systems, and synchronize researcher profiles from HR databases and directory services. This creates a single unified view of institutional research activity that updates automatically as new publications are indexed and new grants are awarded.

CyVerse Atmosphere's API can be integrated with HPC job schedulers (Slurm, PBS) to give researchers a unified dashboard for launching both cloud VMs and traditional cluster jobs from the same web interface. HubZero's Joomla-based architecture provides plugin hooks for connecting to learning management systems, institutional repositories, and data catalogs. The key architectural decision is whether to deploy VIVO as the front-facing researcher portal with Atmosphere and HubZero backing it, or to use HubZero as the primary gateway with VIVO profiles embedded — both patterns are successfully deployed at major research universities.

## FAQ

### What is the difference between a VRE and a project management tool?

While project management tools (like OpenProject or Taiga) focus on tasks, timelines, and resource planning, Virtual Research Environments are domain-aware platforms that understand research-specific concepts: publications, grants, datasets, researcher profiles, and computational workflows. A VRE integrates with academic infrastructure (ORCID, PubMed, DOI registries) and provides capabilities like expertise discovery across institutions — features you would not find in a general-purpose project management system.

### Can VIVO, CyVerse, and HubZero be used together?

Yes, and many institutions do exactly that. VIVO handles researcher profiles and expertise discovery, CyVerse Atmosphere provides the computational infrastructure for running analyses, and HubZero can be the public-facing gateway where the community accesses tools and data. These platforms complement rather than compete with each other. VIVO can link to HubZero-hosted tools from researcher profiles, and Atmosphere can serve as the compute backend for HubZero's simulation tools.

### How do these platforms handle large-scale federated identity?

All three support institutional single sign-on. VIVO has the most comprehensive identity federation support with native Shibboleth and SAML integration — critical for multi-institution research networks where researchers from different universities need seamless access. CyVerse Atmosphere supports LDAP and OAuth2, while HubZero integrates with the Joomla authentication framework supporting LDAP, CAS, and OAuth plugins.

### What is the minimum viable setup for a small research group?

For a small group (5-20 researchers), **HubZero** is the most practical starting point — it can run on a single LAMP server and provides an immediate web presence with project workspaces and simple data sharing. For groups focused on discovering collaborators across departments, **VIVO** with Docker Compose can be up in under an hour and immediately starts mapping your institution's research expertise. **CyVerse Atmosphere** requires an OpenStack deployment, making it suitable for institutions with existing cloud infrastructure rather than small groups starting from scratch.

### How do VREs integrate with existing data repositories?

VIVO uses linked data (RDF) to reference datasets hosted in external repositories like Dataverse, Figshare, or institutional data repositories. CyVerse Atmosphere includes an integrated Data Store backed by iRODS for managing scientific data within the platform. HubZero provides project workspaces and can be extended with connectors to external storage systems. All three can be configured to reference datasets via DOIs, creating traceable links between research outputs and the environments that produced them.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Virtual Research Environments: VIVO vs CyVerse Atmosphere vs HubZero Compared",
  "description": "Comprehensive comparison of self-hosted virtual research environment platforms — VIVO, CyVerse Atmosphere, and HubZero — for research networking, cloud-based scientific computing, and science gateway creation. Includes Docker Compose deployment configs.",
  "datePublished": "2026-06-10",
  "dateModified": "2026-06-10",
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
