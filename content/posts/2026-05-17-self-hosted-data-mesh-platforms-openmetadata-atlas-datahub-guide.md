---
title: "Self-Hosted Data Mesh Platforms: OpenMetadata vs Apache Atlas vs DataHub 2026"
date: "2026-05-17"
tags: ["comparison", "guide", "self-hosted", "data-mesh", "data-governance", "metadata"]
draft: false
description: "Compare self-hosted data mesh platforms — OpenMetadata, Apache Atlas, and DataHub. Learn how to implement domain-oriented data ownership, data products, and federated governance with open-source tools."
---

The data mesh architecture has emerged as a practical response to the limitations of centralized data lakes and warehouses. Rather than funneling all data through a single team or platform, data mesh treats data as a product — owned by domain teams, governed through federated policies, and discoverable through a self-serve metadata layer.

Three open-source platforms have become the leading candidates for implementing data mesh at scale: **OpenMetadata**, **Apache Atlas**, and **DataHub**. Each takes a different approach to metadata management, governance, and discoverability. This guide compares them head-to-head and shows you how to self-host them with Docker Compose.

## What Is Data Mesh?

Data mesh, introduced by Zhamak Dehghani in 2019, is built on four foundational principles:

1. **Domain-oriented data ownership** — Each business domain owns its data pipelines, schemas, and quality standards
2. **Data as a product** — Data is treated like any other product, with SLAs, documentation, and consumers in mind
3. **Self-serve data infrastructure** — A platform team provides the tooling that enables domain teams to build, publish, and consume data products
4. **Federated computational governance** — Global standards (security, compliance) are enforced automatically while domain teams retain autonomy over their data

A metadata platform is the backbone of a data mesh implementation — it provides the catalog for discovery, the governance layer for policy enforcement, and the lineage tracking for accountability.

## Comparison Table

| Feature | OpenMetadata | Apache Atlas | DataHub |
|---------|-------------|--------------|---------|
| **GitHub Stars** | 13,800+ | 2,000+ | 11,800+ |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| **Backend** | Java + Elasticsearch | Java + Atlas Store (HBase/JanusGraph) | Java (GMS) + Elasticsearch + MySQL |
| **UI** | React-based modern UI | Atlas UI (basic web console) | React-based (DataHub React app) |
| **Lineage** | Column-level lineage | Entity-level + column lineage | Column-level lineage |
| **Governance** | Domain-based, test framework | Tag-based classification + glossary | Policy-based governance (data products) |
| **Data Products** | Native support via Domains | Via Business Metadata attributes | Native data product entities |
| **API** | REST + GraphQL | REST | REST + GraphQL (beta) |
| **Ingestion** | Python ingestion framework | Hive/Atlas hooks | Python ingestion framework |
| **Docker Compose** | Yes (official) | Yes (via Docker images) | Yes (official quickstart) |
| **Observability** | Data quality tests, freshness | Classification, entity auditing | Health checks, freshness monitoring |
| **SSO** | LDAP, OIDC, SAML | LDAP, Kerberos | OIDC, SAML |
| **Active Development** | Very active | Steady (Apache project) | Very active (Acryl-sponsored) |

## OpenMetadata

OpenMetadata is a unified metadata platform built from the ground up for modern data teams. It emphasizes collaboration, data quality, and domain-oriented governance — making it a strong fit for data mesh implementations.

### Architecture

OpenMetadata uses a Java-based API server backed by Elasticsearch for search and MySQL/PostgreSQL for persistence. The ingestion framework is Python-based and connects to sources like Snowflake, BigQuery, Kafka, Airflow, and dbt.

### Key Data Mesh Features

- **Domains** — Assign data assets to business domains, enabling decentralized ownership
- **Data Products** — Group related assets under a product with clear ownership and SLAs
- **Data Quality Tests** — Built-in test framework (Great Expectations integration) with column-level validation
- **Column-Level Lineage** — Track data flow from source to consumption with field-level granularity
- **Glossary & Tags** — Standardize terminology across domains with a shared business glossary
- **Team Collaboration** — Comments, descriptions, and ownership assignments foster cross-domain communication

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  openmetadata-server:
    image: docker.open-metadata.org/openmetadata-server:1.5.0
    container_name: openmetadata-server
    depends_on:
      - mysql
      - elasticsearch
    ports:
      - "8585:8585"
    environment:
      - OPENMETADATA_CLUSTER_NAME=openmetadata
      - SERVER_PORT=8585
      - SERVER_ADMIN_PORT=8586
      - LOG4J_CONFIGURATION_FILE=log4j2.xml
      - DB_DRIVER_CLASS=com.mysql.cj.jdbc.Driver
      - DB_SCHEME=mysql
      - DB_PARAMS="sessionVariables=default_storage_engine=InnoDB&useSSL=false&allowPublicKeyRetrieval=true&rewriteBatchedStatements=true"
      - DB_HOST=mysql
      - DB_HOST_PORT=3306
      - DB_USER=openmetadata_user
      - DB_PASSWORD=openmetadata_password
      - DB_DATABASE=openmetadata_db
      - ELASTICSEARCH_HOST=elasticsearch
      - ELASTICSEARCH_PORT=9200
      - ELASTICSEARCH_SCHEME=http
    networks:
      - app_network

  mysql:
    image: mysql:8.4
    container_name: mysql
    ports:
      - "3306:3306"
    environment:
      MYSQL_ROOT_PASSWORD: openmetadata_password
      MYSQL_DATABASE: openmetadata_db
      MYSQL_USER: openmetadata_user
      MYSQL_PASSWORD: openmetadata_password
    networks:
      - app_network

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.14.3
    container_name: elasticsearch
    ports:
      - "9200:9200"
    environment:
      - discovery.type=single-node
      - ES_JAVA_OPTS=-Xms512m -Xmx512m
      - xpack.security.enabled=false
    networks:
      - app_network

networks:
  app_network:
    driver: bridge
```

```bash
# Start OpenMetadata
docker compose up -d

# Access UI at http://localhost:8585
# Default credentials: admin / admin
```

## Apache Atlas

Apache Atlas is a mature metadata management and governance platform for the Hadoop ecosystem. It provides a extensible type system, metadata repository, and integration with the broader Apache data stack.

### Architecture

Apache Atlas runs as a Java service with a pluggable storage backend (Apache HBase, JanusGraph, or embedded Solr). It uses Apache Kafka for event notifications and provides REST APIs for metadata operations.

### Key Data Mesh Features

- **Type System** — Extensible type and classification system for any data asset
- **Business Metadata** — Attach domain-specific attributes to entities
- **Lineage** — Entity-level and column-level lineage tracking through hooks
- **Tags & Classifications** — Automated classification using policies and rules
- **Hive Hook Integration** — Automatic metadata capture from Hive queries
- **REST API** — Full CRUD operations for types, entities, and relationships
- **Security** — LDAP and Kerberos authentication, Ranger integration for authorization

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  apache-atlas:
    image: apache/atlas:2.6.0
    container_name: apache-atlas
    ports:
      - "21000:21000"
    environment:
      - ATLAS_HOME=/opt/atlas
      - ATLAS_SERVER_OPTS="-server -Xmx2048m"
      - ATLAS_SERVER_HEAP="-Xms1024m -Xmx2048m"
    volumes:
      - atlas-data:/opt/atlas/data
      - atlas-conf:/opt/atlas/conf
    networks:
      - app_network

  zookeeper:
    image: zookeeper:3.9
    container_name: zookeeper
    ports:
      - "2181:2181"
    networks:
      - app_network

  solr:
    image: solr:9.6
    container_name: solr
    ports:
      - "8983:8983"
    environment:
      - SOLR_HEAP=512m
    networks:
      - app_network

volumes:
  atlas-data:
  atlas-conf:

networks:
  app_network:
    driver: bridge
```

```bash
# Start Apache Atlas
docker compose up -d

# Access UI at http://localhost:21000
# Default credentials: admin / admin
```

## DataHub

DataHub, originally built at LinkedIn and now a Linux Foundation project, is a metadata platform designed for the modern data stack. It excels at data discovery, lineage, and governance with a focus on developer experience.

### Architecture

DataHub consists of a metadata service (GMS - Generalized Metadata Service) built on Java, backed by Elasticsearch for search, and MySQL for metadata storage. The ingestion framework is Python-based and supports hundreds of sources.

### Key Data Mesh Features

- **Data Products** — Native data product entity type with ownership, SLA, and lifecycle management
- **Domains** — Organize assets by business domain for decentralized governance
- **Policy-Based Governance** — Define access, retention, and quality policies that are enforced automatically
- **Column-Level Lineage** — Track data flow across pipelines with field-level detail
- **Freshness Monitoring** — Automated health checks for dataset staleness
- **Assertions** — Data quality assertions with alerting
- **GraphQL API** — Modern API for querying metadata and building custom integrations
- **Actions Framework** — Event-driven automation (e.g., auto-tag datasets based on content)

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  datahub-gms:
    image: acryldata/datahub-gms:v0.14.1
    container_name: datahub-gms
    ports:
      - "8080:8080"
    depends_on:
      - datahub-mysql
      - datahub-elasticsearch
      - datahub-kafka
    environment:
      - EBEAN_DATASOURCE_HOST=datahub-mysql:3306
      - EBEAN_DATASOURCE_USERNAME=datahub
      - EBEAN_DATASOURCE_PASSWORD=datahub
      - EBEAN_DATASOURCE_URL=jdbc:mysql://datahub-mysql:3306/datahub?useUnicode=yes&characterEncoding=UTF-8
      - ELASTICSEARCH_HOST=datahub-elasticsearch
      - ELASTICSEARCH_PORT=9200
      - KAFKA_BOOTSTRAP_SERVER=datahub-kafka:9092
    networks:
      - datahub_network

  datahub-frontend:
    image: acryldata/datahub-frontend-react:v0.14.1
    container_name: datahub-frontend
    ports:
      - "9002:9002"
    environment:
      - DATAHUB_GMS_HOST=datahub-gms
      - DATAHUB_GMS_PORT=8080
      - ELASTICSEARCH_HOST=datahub-elasticsearch
      - ELASTICSEARCH_PORT=9200
      - DATAHUB_SECRET=change_me
    networks:
      - datahub_network

  datahub-mysql:
    image: mysql:8.0
    container_name: datahub-mysql
    environment:
      MYSQL_ROOT_PASSWORD: secret
      MYSQL_DATABASE: datahub
      MYSQL_USER: datahub
      MYSQL_PASSWORD: datahub
    networks:
      - datahub_network

  datahub-elasticsearch:
    image: elasticsearch:7.17.21
    container_name: datahub-elasticsearch
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms256m -Xmx512m"
      - xpack.security.enabled=false
    networks:
      - datahub_network

  datahub-kafka:
    image: confluentinc/cp-kafka:7.7.0
    container_name: datahub-kafka
    depends_on:
      - datahub-zookeeper
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: datahub-zookeeper:2181
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://datahub-kafka:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    networks:
      - datahub_network

  datahub-zookeeper:
    image: confluentinc/cp-zookeeper:7.7.0
    container_name: datahub-zookeeper
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
    networks:
      - datahub_network

networks:
  datahub_network:
    driver: bridge
```

```bash
# Start DataHub using official quickstart
curl -L https://raw.githubusercontent.com/datahub-project/datahub/master/docker/quickstart/docker-compose.quickstart.yml \
  -o docker-compose.yml
docker compose up -d

# Or use the official CLI
pip install acryl-datahub
datahub docker quickstart

# Access UI at http://localhost:9002
# Default credentials: datahub / datahub
```

## Choosing the Right Platform

### OpenMetadata is best when:
- You want the most modern, user-friendly UI out of the box
- Domain-based governance is your primary requirement
- Built-in data quality testing is important
- You prefer a simpler deployment (MySQL + Elasticsearch)

### Apache Atlas is best when:
- You're already invested in the Apache/Hadoop ecosystem
- You need deep integration with Hive, Sqoop, or Storm
- Kerberos-based security is a requirement
- You need an extensible type system for custom entity types

### DataHub is best when:
- You need the richest ingestion ecosystem (200+ source connectors)
- Data product lifecycle management is critical
- You want event-driven automation through the Actions framework
- GraphQL API access is important for custom integrations

## Why Self-Host Your Data Mesh Platform?

Data governance and metadata management are foundational to any organization's data strategy. Self-hosting your data mesh platform provides several critical advantages over SaaS alternatives:

**Data sovereignty and compliance.** Metadata about your data assets — including PII classifications, access patterns, and lineage — is sensitive information. Self-hosting ensures this metadata never leaves your infrastructure, helping you comply with GDPR, HIPAA, and other regulatory requirements that mandate data locality.

**No vendor lock-in.** SaaS metadata platforms can change their pricing models, deprecate features, or discontinue services without warning. Self-hosted open-source platforms give you full control over your metadata infrastructure roadmap, with the ability to fork, customize, or migrate as needed.

**Integration with internal systems.** Self-hosted platforms can connect directly to your internal databases, data warehouses, and message queues without requiring network peering or API gateways that SaaS platforms demand. This reduces latency and eliminates data transfer costs.

**Cost predictability.** Cloud-hosted metadata platforms typically charge per asset, per user, or per API call — costs that scale unpredictably as your data ecosystem grows. Self-hosted platforms have fixed infrastructure costs regardless of asset count, making budgeting straightforward.

**Custom governance policies.** Self-hosting allows you to implement organization-specific governance rules directly in the platform codebase or configuration, without waiting for a vendor to support your use case. For organizations with complex compliance requirements, this flexibility is essential.

For data pipeline orchestration, see our [Airflow vs Dagster vs Prefect comparison](../2026-05-07-dagster-vs-airflow-vs-prefect-data-pipeline-orchestration-ui-guide/). If you need data quality testing, check our [Great Expectations vs Soda vs dbt guide](../self-hosted-data-quality-tools-great-expectations-soda-dbt-guide-2026/). For broader data catalog needs, our [Amundsen vs DataHub vs OpenMetadata comparison](../amundsen-vs-datahub-vs-openmetadata-self-hosted-data-catalog-guide/) covers the discovery angle.

## FAQ

### What is the difference between a data catalog and a data mesh platform?

A data catalog focuses on metadata discovery — helping users find and understand datasets. A data mesh platform goes further by implementing the organizational principles of data mesh: domain ownership, data as a product, self-serve infrastructure, and federated governance. OpenMetadata, Apache Atlas, and DataHub all function as data catalogs, but they also provide the governance and domain features needed for data mesh.

### Can I migrate from a centralized data lake to a data mesh architecture?

Yes. The typical migration path involves: (1) identifying domain boundaries in your existing data lake, (2) assigning ownership of each data domain to the responsible team, (3) setting up a metadata platform to catalog assets by domain, (4) implementing data quality tests and SLAs per domain, and (5) gradually decomposing centralized pipelines into domain-owned pipelines. All three platforms support this migration pattern.

### Do these platforms support real-time metadata ingestion?

OpenMetadata and DataHub support real-time metadata ingestion through their Python ingestion frameworks, which can be scheduled to run continuously or triggered by pipeline events. Apache Atlas supports real-time metadata capture through Hive hooks and Kafka-based notifications. For streaming metadata updates, DataHub's Kafka-based architecture provides the lowest latency.

### How do these platforms handle data quality?

OpenMetadata has a built-in data quality test framework with 40+ test types (uniqueness, null checks, range validation) and Great Expectations integration. DataHub provides assertions with freshness monitoring and automated alerting. Apache Atlas relies on external integrations (e.g., Apache Griffin) for data quality checks rather than providing a native test framework.

### Which platform is easiest to deploy?

OpenMetadata has the simplest deployment: a Docker Compose file with MySQL and Elasticsearch. DataHub requires more services (GMS, frontend, MySQL, Elasticsearch, Kafka, ZooKeeper) but provides a `datahub docker quickstart` command. Apache Atlas has the most complex deployment due to its Hadoop ecosystem dependencies, though Docker images simplify the process.

### Can these platforms integrate with cloud data warehouses?

All three platforms support cloud data warehouse metadata ingestion. OpenMetadata and DataHub have native connectors for Snowflake, BigQuery, Redshift, and Databricks. Apache Atlas has connectors for AWS Glue, Azure Purview, and can be extended for cloud warehouses through its type system.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Data Mesh Platforms: OpenMetadata vs Apache Atlas vs DataHub 2026",
  "description": "Compare self-hosted data mesh platforms — OpenMetadata, Apache Atlas, and DataHub. Learn how to implement domain-oriented data ownership, data products, and federated governance with open-source tools.",
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
