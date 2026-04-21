---
title: "OpenLineage vs DataHub vs Apache Atlas: Self-Hosted Data Lineage Guide 2026"
date: 2026-04-20
tags: ["comparison", "guide", "self-hosted", "data-lineage", "metadata", "data-engineering"]
draft: false
description: "Compare OpenLineage, DataHub, and Apache Atlas for self-hosted data lineage tracking. Docker configs, integration guides, and feature comparison for data engineers building observable pipelines."
---

Data lineage — the ability to track where data comes from, how it transforms, and where it ends up — has become essential for any organization running non-trivial data pipelines. When a dashboard shows a wrong number, lineage tells you exactly which upstream table, job, or transformation introduced the error. When regulators ask where personal data flows, lineage provides the audit trail.

If you are building or maintaining self-hosted data infrastructure, choosing the right lineage tool matters. This guide compares three of the most mature open-source options: **OpenLineage** (with its Marquez server), **DataHub**, and **Apache Atlas**.

## Why Track Data Lineage?

Self-hosting your data lineage infrastructure gives you full control over sensitive metadata — table schemas, job definitions, PII column tags, and business glossary terms never leave your network. Cloud-native lineage tools often require sending this metadata to external SaaS platforms, which is unacceptable for organizations with strict data residency or compliance requirements.

Lineage tracking solves several real problems:

- **Root cause analysis**: When a downstream report breaks, trace back through the pipeline to find the failing job or stale source table in seconds instead of hours.
- **Impact analysis**: Before changing a column type or dropping a table, see exactly which dashboards, models, and pipelines depend on it.
- **Regulatory compliance**: GDPR, CCPA, and SOX all require demonstrating control over personal and financial data flows. Lineage provides the evidence.
- **Data trust**: Analysts and business users can see where their numbers come from, increasing confidence in self-service analytics.

For related reading, see our [self-hosted data catalog guide](../amundsen-vs-datahub-vs-openmetadata-self-hosted-data-catalog-guide/) for metadata discovery tools and our [Airflow vs Prefect vs Dagster comparison](../apache-airflow-vs-prefect-vs-dagster-self-hosted-data-orchestration-guide/) for pipeline orchestration platforms that integrate with lineage systems.

## What Makes a Good Data Lineage Tool?

Before comparing specific tools, here are the capabilities you should evaluate:

| Capability | Why It Matters |
|---|---|
| **Column-level lineage** | Track individual column transformations, not just table-to-table flow |
| **Open standard support** | Avoid vendor lock-in; OpenLineage is becoming the industry standard |
| **Pipeline integrations** | Native support for Airflow, Spark, dbt, Flink, and other engines |
| **Search and discovery** | Query lineage graphs programmatically and via a web UI |
| **Metadata storage** | How lineage events are persisted (PostgreSQL, Elasticsearch, graph DB) |
| **Access control** | Role-based permissions for sensitive lineage data |
| **Scalability** | Handle millions of lineage events per day in production |

## OpenLineage + Marquez: The Open Standard

OpenLineage is an open standard for collecting and sharing lineage metadata. It defines a JSON-based event model that captures dataset inputs, outputs, and the job that performed the transformation. The standard is maintained under the Linux Foundation's LF AI & Data umbrella.

Marquez is the reference implementation — a lineage server that receives OpenLineage events, stores them in PostgreSQL, and exposes a REST API and web UI for querying lineage graphs. The Marquez project was originally developed at WeWork and is now part of the OpenLineage ecosystem.

**GitHub stats**: 2,416 stars (OpenLineage org), last updated April 2026, primarily Java.

### Key Features

- **OpenLineage native**: First-class support for the OpenLineage event format — no translation layer needed
- **Column-level lineage**: Captures field-level transformations when integrations provide the data
- **Run lifecycle tracking**: Tracks job runs with start, complete, and failed states
- **REST API**: Full CRUD access to datasets, jobs, runs, and lineage graphs
- **Web UI**: Visual lineage graph with clickable nodes for exploring upstream and downstream dependencies
- **PostgreSQL backend**: Simple, reliable storage that is easy to back up and scale

### [docker](https://www.docker.com/) Compose Setup

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: marquez
      POSTGRES_PASSWORD: marquez
      POSTGRES_DB: marquez
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U marquez"]
      interval: 5s
      timeout: 5s
      retries: 5

  marquez:
    image: marquezproject/marquez:latest
    ports:
      - "5000:5000"
      - "5001:5001"
    environment:
      MARQUEZ_URL: http://localhost:5000
      MARQUEZ_DB_URL: jdbc:postgresql://postgres:5432/marquez
      MARQUEZ_DB_USER: marquez
      MARQUEZ_DB_PASSWORD: marquez
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  postgres_data:
```

### Integrating with Apache Airflow

Install the OpenLineage Airflow provider and configure it in your Airflow deployment:

```bash
pip install openlineage-airflow
```

Set the following environment variables on your Airflow workers:

```bash
export OPENLINEAGE_URL=http://marquez:5000
export OPENLINEAGE_NAMESPACE=default
export OPENLINEAGE_API_KEY=  # optional, for authenticated endpoints
```

Once configured, every Airflow task execution automatically emits OpenLineage events to Marquez — no code changes to your DAGs required.

### Integrating with dbt

The dbt OpenLineage integration captures column-level lineage from your dbt models:

```bash
pip install openlineage-dbt
```

Add to your `dbt_project.yml`:

```yaml
config-version: 2
require-dbt-version: ">=1.0.0"

vars:
  openlineage:
    url: http://marquez:5000
    namespace: my_dbt_project
```

Run `dbt run` and lineage events flow into Marquez automatically, capturing source-to-target column mappings from your dbt models.

## DataHub: The Comprehensive Metadata Platform

DataHub, originally built at LinkedIn and now an LF AI & Data project, is a full-featured metadata platform that includes data lineage as one of its core capabilities. It goes beyond lineage to offer data discovery, governance, quality monitoring, and a business glossary.

**GitHub stats**: 11,814 stars, last updated April 2026, primarily Java.

### Key Features

- **Unified metadata platform**: Lineage, discovery, governance, quality, and ownership in one system
- **Column-level lineage**: Native support through ingestion from dbt, Airflow, Spark, Snowflake, and more
- **GraphQL API**: Powerful query language for building custom lineage applications
- **Elasticsearch backend**: Full-text search across all metadata entities
- **Policy engine**: Fine-grained access control using role-based and attribute-based policies
- **Data contracts**: Define and enforce expectations on datasets
- **Business glossary**: Tag datasets with business terms for non-technical users

### Docker Compose Setup (Quick Start)

DataHub provides an official quick-start compose file that runs all dependencies:

```bash
# Download the official quick-start compose
curl -L https://raw.githubusercontent.com/datahub-project/datahub/master/docker/quickstart/docker-compose.quickstart.yml -o docker-compose.yml

# Start all servi[kafka](https://kafka.apache.org/)Elasticsearch, MySQL, Kafka, ZooKeeper, DataHub GMS, Frontend)
docker compose -f docker-compose.yml up -d
```

For production deployments, DataHub recommends running components separately with proper resource allocation:

```yaml
version: "3.8"

services:
  datahub-gms:
    image: linkedin/datahub-gms:head
    ports:
      - "8080:8080"
    environment:
      EBEAN_DATASOURCE_HOST: mysql:3306
      EBEAN_DATASOURCE_URL: jdbc:mysql://mysql:3306/datahub
      EBEAN_DATASOURCE_USERNAME: datahub
      EBEAN_DATASOURCE_PASSWORD: datahub
      KAFKA_BOOTSTRAP_SERVER: kafka:9092
      ELASTICSEARCH_HOST: elasticsearch
      ELASTICSEARCH_PORT: 9200
    depends_on:
      - mysql
      - kafka
      - elasticsearch

  datahub-frontend-react:
    image: linkedin/datahub-frontend-react:head
    ports:
      - "9002:9002"
    environment:
      DATAHUB_GMS_HOST: datahub-gms
      DATAHUB_GMS_PORT: 8080
      DATAHUB_SECRET: secret
    depends_on:
      - datahub-gms

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_DATABASE: datahub
      MYSQL_USER: datahub
      MYSQL_PASSWORD: datahub
      MYSQL_ROOT_PASSWORD: root
    volumes:
      - mysql_data:/var/lib/mysql

  elasticsearch:
    image: elasticsearch:8.11.0
    environment:
      discovery.type: single-node
      ES_JAVA_OPTS: -Xms512m -Xmx512m
    volumes:
      - es_data:/usr/share/elasticsearch/data

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
    depends_on:
      - zookeeper

  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

volumes:
  mysql_data:
  es_data:
```

### Ingesting Lineage from Airflow

Use the DataHub Airflow plugin to emit metadata events:

```bash
pip install "acryl-datahub-airflow-plugin"
```

Configure in your Airflow connection settings:

```bash
export DATAHUB_GMS_URL=http://datahub-gms:8080
export DATAHUB_GMS_TOKEN=your-urn:li:corpuser:admin-token
```

The plugin sends both operational metadata (task runs, durations) and entity metadata (dataset schemas, lineage edges) to DataHub on every task execution.

## Apache Atlas: Hadoop Ecosystem Governance

Apache Atlas is a metadata management and governance framework for the Hadoop ecosystem. It provides data classification, lineage tracking, and security policy enforcement for Hadoop-based data platforms. While newer than OpenLineage and DataHub in terms of developer experience, Atlas remains the go-to choice for organizations running Hadoop, Hive, and Ranger.

**GitHub stats**: 2,091 stars, last updated April 2026, primarily Java.

### Key Features

- **Hadoop-native**: Deep integration with Hive, HBase, Sqoop, Storm, and Kafka
- **Type system**: Define custom metadata types and attach them to any entity
- **Classification and tagging**: Apply security classifications (PII, PCI, PHI) that propagate through lineage
- **Ranger integration**: Apache Ranger policies can use Atlas tags for fine-grained access control
- **REST API and UI**: Web console for browsing entities, searching metadata, and viewing lineage graphs
- **Hook-based ingestion**: Atlas hooks in Hive, Spark, and Sqoop automatically capture metadata

### Docker Compose Setup

Apache Atlas does not ship an official Docker image, but the community maintains workable setups. Here is a minimal configuration using the Atlas source build:

```yaml
version: "3.8"

services:
  solr:
    image: solr:9.4
    ports:
      - "8983:8983"
    command: solr start -f
    volumes:
      - solr_data:/var/solr

  atlas:
    build:
      context: .
      dockerfile: Dockerfile.atlas
    ports:
      - "21000:21000"
    environment:
      ATLAS_HOME: /opt/atlas
      JAVA_HOME: /usr/lib/jvm/java-11-openjdk
    depends_on:
      - solr
    volumes:
      - atlas_data:/opt/atlas/data

volumes:
  solr_data:
  atlas_data:
```

For the `Dockerfile.atlas`, build Apache Atlas from source and configure it to use Solr for search indexing and the embedded HBase storage backend. In production, most deployments run Atlas on dedicated VMs alongside their Hadoop clusters rather than in containers.

### Ingesting Lineage from Hive

Enable the Hive hook in `hive-site.xml`:

```xml
<property>
  <name>hive.exec.post.hooks</name>
  <value>org.apache.atlas.hive.hook.HiveHook</value>
</property>

<property>
  <name>atlas.hook.hive.synchronous</name>
  <value>false</value>
</property>

<property>
  <name>atlas.hook.hive.numRetries</name>
  <value>3</value>
</property>
```

Once configured, every Hive query execution automatically creates or updates Atlas entities with column-level lineage information.

## Feature Comparison

| Feature | OpenLineage + Marquez | DataHub | Apache Atlas |
|---|---|---|---|
| **Primary Focus** | Lineage events | Full metadata platform | Hadoop governance |
| **Column-Level Lineage** | Yes | Yes | Yes |
| **Open Standard** | OpenLineage (native) | Open metadata model | Custom type system |
| **Storage Backend** | PostgreSQL | MySQL + Elasticsearch | HBase + Solr |
| **API** | REST | GraphQL + REST | REST |
| **Web UI** | Lineage graph | Full metadata browser | Entity browser + lineage |
| **Airflow Integration** | Native provider | Plugin available | Manual hook setup |
| **dbt Integration** | Native adapter | Native adapter | Not available |
| **Spark Integration** | Native agent | Native hook | Native hook |
| **Access Control** | Basic API auth | RBAC + ABAC policies | Ranger integration |
| **Business Glossary** | No | Yes | Yes |
| **Data Quality** | No | Yes (via tests) | Limited |
| **Hadoop Ecosystem** | Limited | Moderate | Excellent |
| **Docker Support** | First-class | Official quick-start | Community images |
| **Stars (GitHub)** | 2,416 | 11,814 | 2,091 |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |

## Which Tool Should You Choose?

### Choose OpenLineage + Marquez If

- Your primary need is **pipeline observability** — tracking job runs and data flow
- You want the **simplest deployment** — a single PostgreSQL database and one service
- You are building a **modern data stack** with Airflow, dbt, Spark, or Flink
- You want to use the **OpenLineage standard** to avoid vendor lock-in
- You do not need a business glossary or data quality features

Marquez is the leanest option. Get it running in minutes with the Docker compose above, connect your Airflow or dbt pipelines, and start querying lineage through the REST API.

### Choose DataHub If

- You need a **unified metadata platform** — discovery, lineage, governance, and quality in one system
- You want **business glossary** support for bridging technical and business terminology
- You need **fine-grained access control** with RBAC and ABAC policies
- You are already using **Kafka and Elasticsearch** in your infrastructure
- You want the **most active open-source community** — 11,000+ stars and hundreds of contributors

DataHub is the most feature-complete option. The tradeoff is operational com[plex](https://www.plex.tv/)ity — running Kafka, Elasticsearch, MySQL, and multiple DataHub services requires more infrastructure than Marquez.

### Choose Apache Atlas If

- You are running a **Hadoop-based data platform** — Hive, HBase, Sqoop, or Storm
- You need **Ranger integration** for security policy enforcement using Atlas classifications
- You want **custom type definitions** to model your domain-specific metadata
- Your organization already uses the **Hadoop ecosystem** extensively

Atlas is the most specialized option. If you are not running Hadoop, the operational overhead outweighs the benefits compared to Marquez or DataHub.

## FAQ

### What is the difference between data lineage and a data catalog?

A data catalog focuses on metadata discovery — helping users find datasets, understand their schemas, and see ownership information. Data lineage focuses on the flow of data — showing how datasets are created, transformed, and consumed across pipelines. The two are complementary: many teams use both together. DataHub and Apache Atlas include both capabilities, while Marquez focuses on lineage specifically.

### Can OpenLineage work without Marquez?

Yes. OpenLineage is a standard, not a product. You can send OpenLineage events to any server that implements the OpenLineage API, including custom-built backends. Marquez is the reference implementation, but alternatives like DataHub also accept OpenLineage-formatted events through their ingestion framework.

### Does DataHub replace Apache Atlas?

For most organizations not running Hadoop, yes. DataHub covers the same metadata management and lineage use cases with a more modern architecture (GraphQL API, Kafka-based ingestion, Elasticsearch search). However, Atlas has deeper integration with Hadoop ecosystem tools like Hive hooks and Ranger security policies, which may be critical for Hadoop-centric teams.

### How much infrastructure does each tool require?

Marquez needs PostgreSQL and one application server — roughly 2 containers. DataHub requires Elasticsearch, MySQL, Kafka, ZooKeeper, GMS, and the frontend — 6+ containers in the quick-start setup. Apache Atlas needs Solr (for search) and HBase (for storage) plus the Atlas server itself — 3+ services. For teams with limited infrastructure, Marquez is the easiest to operate.

### Can I migrate lineage data between these tools?

OpenLineage events are portable by design since they follow a standard JSON schema. If you are currently sending events to Marquez, you can redirect them to a DataHub ingestion sink or a custom OpenLineage consumer. Atlas uses its own entity model, so migration requires translating Atlas types and entities into the target format.

### Is column-level lineage supported by all three tools?

Yes, but the quality of column-level lineage depends on the integration. OpenLineage captures column-level details from dbt and Spark integrations. DataHub inherits column-level lineage from its ingestion sources (dbt, Airflow, Spark, Snowflake). Apache Atlas captures column lineage through Hive and Spark hooks. If column-level tracking is critical, test your specific pipeline integrations before committing to a tool.

### Are these tools suitable for small teams?

Marquez is well-suited for small teams — it deploys quickly, requires minimal resources, and the OpenLineage integrations work out of the box with Airflow and dbt. DataHub can work for small teams if you are comfortable managing Kafka and Elasticsearch, or you can use the managed DataHub Cloud offering. Apache Atlas is generally overkill for small teams unless you are already running Hadoop.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "OpenLineage vs DataHub vs Apache Atlas: Self-Hosted Data Lineage Guide 2026",
  "description": "Compare OpenLineage, DataHub, and Apache Atlas for self-hosted data lineage tracking. Docker configs, integration guides, and feature comparison for data engineers building observable pipelines.",
  "datePublished": "2026-04-20",
  "dateModified": "2026-04-20",
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
