---
title: "Amundsen vs DataHub vs OpenMetadata: Self-Hosted Data Catalog Guide 2026"
date: 2026-04-15
tags: ["comparison", "guide", "self-hosted", "data-catalog", "metadata"]
draft: false
description: "Compare the top three open-source data catalog and metadata management platforms — Amundsen, DataHub, and OpenMetadata — with practical self-hosted deployment guides, feature comparisons, and recommendations for 2026."
---

Modern organizations manage hundreds of databases, data lakes, warehouses, and streaming pipelines. Finding the right dataset, understanding its lineage, knowing who owns it, and trusting its quality are daily challenges for data teams. Commercial data catalogs like Alation, Collibra, and Informatica Enterprise Data Catalog charge premium prices and lock your metadata behind proprietary formats.

Open-source data catalogs solve this problem differently: they give you full control over your metadata, run on your own infrastructure, and integrate with the tools you already use. This guide compares the three leading open-source data catalog platforms — Amundsen, DataHub, and OpenMetadata — with practical deployment instructions so you can choose and deploy the right solution for your organization.

## Why You Need a Self-Hosted Data Catalog

A data catalog is a centralized inventory of all your data assets — tables, columns, dashboards, pipelines, and machine learning models — enriched with metadata that makes them discoverable, understandable, and trustworthy. Here is why self-hosting matters:

- **Data privacy and compliance.** Metadata often reveals sensitive information about your business: table schemas, data lineage, ownership, and usage patterns. Self-hosting keeps this intelligence within your network, avoiding exposure to third-party SaaS vendors.
- **No per-user licensing fees.** Commercial catalogs charge per seat, making them prohibitively expensive for large organizations. Open-source tools scale to hundreds or thousands of users at zero additional license cost.
- **Deep integration flexibility.** Open-source catalogs expose APIs and plugin architectures that let you connect to internal systems, custom metadata sources, and proprietary tools that commercial products simply cannot integrate with.
- **Metadata ownership.** Your metadata graph — the relationships between tables, pipelines, dashboards, and teams — is a strategic asset. Self-hosting means you own this graph permanently, with no risk of vendor lock-in or service discontinuation.
- **Air-gapped and regulated environments.** Government, healthcare, and financial organizations often operate in air-gapped or heavily regulated environments where SaaS data catalogs are not an option.

## What to Look for in a Data Catalog

Not all data catalogs are equal. When evaluating platforms, focus on these capabilities:

| Capability | Why It Matters |
|---|---|
| **Automated metadata ingestion** | Manual metadata entry does not scale. The catalog must pull schema, statistics, and lineage from your data sources automatically. |
| **Data lineage visualization** | Understanding where data comes from and where it flows is essential for debugging pipelines and regulatory compliance. |
| **Search and discovery** | Users must find datasets quickly using natural language, tag search, or column-level search. |
| **Column-level metadata** | Descriptions, data types, PII tags, and ownership at the column level, not just the table level. |
| **Data quality integration** | Integration with data quality tools (Great Expectations, dbt tests) so users see health scores when browsing datasets. |
| **Access control** | Fine-grained permissions for who can view, edit, or manage metadata. |
| **Business glossary** | A shared vocabulary that maps business terms to technical assets, bridging the gap between analysts and engineers. |
| **Extensibility** | Plugin architecture for custom ingestion sources, metadata transformers, and UI extensions. |

## Overview: Amundsen vs DataHub vs OpenMetadata

### Amundsen — The Pioneer

Amundsen was created by Lyft in 2019 and donated to the Linux Foundation's LF AI & Data organization. It was one of the first open-source data catalogs and remains focused on data discovery and search. Its architecture uses Elasticsearch for search, Neo4j for the metadata graph, and a React-based frontend.

**Strengths:**
- Simple, clean search-first interface
- Strong integration with Presto, Hive, and BigQuery
- Mature preview functionality for seeing sample data
- Active community with Lyft engineering backing
- Lightweight deployment footprint compared to alternatives

**Weaknesses:**
- No built-in data lineage visualization (requires third-party plugins)
- Limited metadata editing capabilities in the UI
- No native business glossary feature
- Smaller plugin ecosystem compared to DataHub
- Development pace has slowed in recent years

### DataHub — The Modern Platform

DataHub was open-sourced by LinkedIn in 2020 and is now maintained by Acryl Data and an active open-source community. It has become the most feature-complete open-source data catalog, with extensive ingestion capabilities, real-time metadata streaming via Kafka, and a robust GraphQL API.

**Strengths:**
- Most comprehensive ingestion framework with 80+ built-in source connectors
- Real-time metadata updates via Kafka-based event streaming
- Rich data lineage visualization (column-level, multi-hop)
- Native business glossary and data product concepts
- Active development with frequent releases
- Strong API-first design with GraphQL and REST endpoints
- Built-in data quality insights integration

**Weaknesses:**
- Com[plex](https://www.plex.tv/) architecture with many dependencies (Kafka, Elasticsearch, MySQL, ZooKeeper)
- Higher operational overhead for self-hosting
- Steeper learning curve for administrators
- UI can feel overwhelming with its density of features

### OpenMetadata — The Collaborative Choice

OpenMetadata was launched in 2021 by the former CEO of DataHub at LinkedIn. It positions itself as a metadata standard and collaboration platform. Its distinguishing features include a standardized metadata schema (using JSON Schema), built-in data quality monitoring, team collaboration tools, and an intuitive user interface.

**Strengths:**
- Standardized metadata schema based on JSON Schema definitions
- Built-in data quality tests and observability features
- Clean, intuitive user interface with collaborative editing
- Team and ownership workflows built into the core product
- Automated metadata ingestion with a well-documented ingestion framework
- Active open-source community and commercial support from the creators
- Native integration with dbt, Airflow, Great Expectations, and more

**Weaknesses:**
- Newer project with a shorter track record than Amundsen
- Fewer third-party integrations than DataHub
- The ingestion framework uses a custom Python SDK rather than a generic connector model
- Community size is smaller than DataHub's

## Feature Comparison

| Feature | Amundsen | DataHub | OpenMetadata |
|---|---|---|---|
| **Search engine** | Elasticsearch | Elasticsearch | Elasticsearch |
| **Metadata store** | Neo4j | MySQL/MariaDB | MySQL/PostgreSQL |
| **Data lineage** | Plugin-based | Native, column-level | Native, column-level |
| **Business glossary** | No | Yes | Yes |
| **Data quality** | Limited | Via Great Expectations | Built-in tests |
| **API** | REST | GraphQL + REST | REST |
| **Ingestion sources** | ~25 | 80+ | 50+ |
| **Real-time updates** | No | Yes (Kafka) | Partial |
| **Access control** | Basic | RBAC + Policies | RBAC |
| **UI customization** | Limited [docker](https://www.docker.com/)rate | Good |
| **Docker deployment** | Yes |[kubernetes](https://kubernetes.io/)er-compose) | Yes (docker-compose) |
| **Kubernetes support** | Via Helm | Via Helm | Via Helm |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |

## Deployment Guide: Self-Hosting Each Platform

### Deploying Amundsen with Docker Compose

Amundsen is the lightest of the three to deploy. Its Docker Compose setup brings up the frontend, metadata service, search service, and their dependencies.

```bash
# Clone the Amundsen repository
git clone https://github.com/amundsen-io/amundsen.git
cd amundsen

# Start all services
docker compose -f docker-amundsen.yml up -d

# Verify services are running
docker compose -f docker-amundsen.yml ps

# Access the UI at http://localhost:5000
```

The default setup includes:
- **Frontend** (port 5000) — React-based search and discovery UI
- **Metadata Service** (port 5002) — Flask-based API for metadata CRUD
- **Search Service** (port 9200) — Elasticsearch instance
- **Neo4j** (port 7687) — Graph database for metadata relationships

To ingest metadata from a PostgreSQL database:

```python
# ingest_postgres.py
from amundsen_gremlin.neo4j_loader import Neo4jLoader
from databuilder.extractors.mysql_extractor import MySQLExtractor
from databuilder.loader.file_system_elasticsearch_json_loader import FSElasticsearchJSONLoader

# Configure the extractor
task = ElasticsearchPublisher()
task.init(
    config={
        'extractor.mysql.metadata': {
            'where_clause': '',
            'model_name': 'mysql_metadata',
            'conn_string': 'mysql://user:password@localhost:3306/db'
        },
        'publisher.elasticsearch': {
            'file_path': '/tmp/elasticsearch.json'
        }
    }
)
task.run()
```

### Deploying DataHub with Docker Compose

DataHub requires more infrastructure but provides a richer feature set. The official quickstart uses Docker Compose with Kafka, Elasticsearch, MySQL, and ZooKeeper.

```bash
# Install the DataHub CLI
pip install acryl-datahub

# Start DataHub with the quickstart Docker Compose
datahub docker quickstart

# This starts:
# - DataHub GMS (Generalized Metadata Service)
# - DataHub Frontend
# - Kafka + ZooKeeper (metadata event streaming)
# - Elasticsearch (search index)
# - MySQL (metadata storage)
# - DataHub Actions (automated metadata processing)

# Wait for all services to be healthy
docker compose ps

# Access the UI at http://localhost:9002
# Default credentials: datahub / datahub
```

To ingest metadata from Snowflake:

```bash
# Create a recipe file: snowflake_recipe.yaml
source:
  type: snowflake
  config:
    account_id: "your_account"
    username: "your_user"
    password: "your_password"
    warehouse: "COMPUTE_WH"
    database: "ANALYTICS"

sink:
  type: "datahub-rest"
  config:
    server: "http://localhost:8080"
    token: "your_datahub_token"
```

```bash
# Run the ingestion
datahub ingest -c snowflake_recipe.yaml --dry-run   # Preview changes
datahub ingest -c snowflake_recipe.yaml              # Execute ingestion
```

For dbt metadata ingestion:

```bash
# Create a dbt recipe: dbt_recipe.yaml
source:
  type: dbt
  config:
    manifest_path: "/path/to/dbt/target/manifest.json"
    catalog_path: "/path/to/dbt/target/catalog.json"
    target_platform: "postgres"

sink:
  type: "datahub-rest"
  config:
    server: "http://localhost:8080"
```

```bash
datahub ingest -c dbt_recipe.yaml
```

To deploy DataHub on Kubernetes with Helm:

```bash
# Add the DataHub Helm repository
helm repo add datahub https://helm.datahubproject.io/
helm repo update

# Install DataHub
helm install datahub datahub/datahub \
  --namespace datahub \
  --create-namespace \
  --set mysql.enabled=true \
  --set elasticsearch.enabled=true \
  --set kafka.enabled=true \
  --set datahub-gms.resources.requests.memory="2Gi"

# Check deployment status
kubectl get pods -n datahub
```

### Deploying OpenMetadata with Docker Compose

OpenMetadata offers a clean deployment experience with well-organized Docker Compose files and a straightforward ingestion framework.

```bash
# Clone the OpenMetadata repository
git clone https://github.com/open-metadata/OpenMetadata.git
cd OpenMetadata/openmetadata-docker

# Start the services (includes MySQL, Elasticsearch, and the OpenMetadata server)
./docker/start.sh

# Or use Docker Compose directly:
docker compose -f docker-compose.yml up -d

# Services started:
# - OpenMetadata Server (port 8585)
# - OpenMetadata UI (port 3000)
# - MySQL (metadata storage)
# - Elasticsearch (search index)

# Access the UI at http://localhost:3000
# Default credentials: admin / admin
```

To ingest metadata from a PostgreSQL database:

```yaml
# postgres_ingestion.yaml
source:
  type: postgres
  serviceName: "production_postgres"
  serviceConnection:
    config:
      type: Postgres
      hostPort: "localhost:5432"
      username: "reader"
      password: "secure_password"
      database: "analytics"
      schemaFilterPattern: ["public", "staging"]

sink:
  type: metadata-rest
  config:
    apiEndpoint: "http://localhost:8585/api"
    auth:
      provider: openmetadata
      config:
        className: "openmetadata.auth.basic.BasicAuthProvider"
        username: "admin"
        password: "admin"
```

```bash
# Install the ingestion framework
pip install "openmetadata-ingestion[postgres]"

# Run ingestion
metadata ingest -c postgres_ingestion.yaml
```

To run data quality tests with OpenMetadata:

```yaml
# data_quality_test.yaml
source:
  type: metadata
  config:
    apiEndpoint: "http://localhost:8585/api"
    auth:
      provider: openmetadata
      config:
        className: "openmetadata.auth.basic.BasicAuthProvider"
        username: "admin"
        password: "admin"

processor:
  type: orm-processor
  config:
    profile_sample_query_percent: 10
    include_tables: true
    include_views: true

sink:
  type: metadata-rest
  config:
    apiEndpoint: "http://localhost:8585/api"
    auth:
      provider: openmetadata
      config:
        className: "openmetadata.auth.basic.BasicAuthProvider"
        username: "admin"
        password: "admin"
```

```bash
metadata ingest -c data_quality_test.yaml
```

## Real-World Usage Scenarios

### Small Data Team (5-15 people)

For a small team, **OpenMetadata** offers the best balance of features and operational simplicity. Its Docker Compose deployment is straightforward, the UI is intuitive, and the built-in data quality features cover most needs without additional tooling. A single engineer can manage the deployment, and the team benefits from collaborative metadata editing.

```bash
# Minimal OpenMetadata setup for a small team
# Add reverse proxy with basic auth for security
docker compose -f docker-compose.yml -f overlays/nginx-proxy.yml up -d
```

### Mid-Size Organization (50-200 data users)

At this scale, **DataHub** shines. Its extensive connector ecosystem means it can ingest metadata from virtually every data source in your stack. The real-time metadata streaming ensures that catalog updates propagate immediately, and the business glossary feature helps maintain a shared vocabulary across teams.

```bash
# Production DataHub setup with external dependencies
# Use managed Kafka and Elasticsearch instead of embedded
datahub docker quickstart \
  --no-elasticsearch \
  --no-kafka \
  --no-mysql
# Then configure external services in datahub.env
```

### Enterprise (500+ users, regulated industry)

For regulated enterprises, **Amundsen** or **DataHub** with custom plugins is often the choice. Amundsen's mature access controls and audit trail capabilities meet compliance requirements, while DataHub's policy framework enables fine-grained metadata governance. In some organizations, running both — Amundsen for discovery and DataHub for governance — provides comprehensive coverage.

## Cost Comparison

Self-hosting eliminates per-user licensing fees, but infrastructure costs still apply:

| Platform | Minimum Infrastructure | Estimated Monthly Cost (cloud) |
|---|---|---|
| Amundsen | 2 CPU, 8 GB RAM, Elasticsearch + Neo4j | $80-150 |
| DataHub | 4 CPU, 16 GB RAM, Kafka + ES + MySQL | $150-300 |
| OpenMetadata | 4 CPU, 12 GB RAM, ES + MySQL | $120-250 |

Compare this to commercial alternatives: Alation starts at $15,000/year for 10 users, and Collibra pricing typically exceeds $50,000/year. For organizations with 100+ data users, the savings from self-hosting are substantial.

## Making the Decision

Choose **Amundsen** if:
- You want the simplest possible deployment
- Search and discovery are your primary needs
- You have a Presto/Hive-heavy stack
- You prefer a lightweight, focused tool

Choose **DataHub** if:
- You need the broadest possible integration coverage
- Real-time metadata updates are important
- Your organization needs a business glossary and data products
- You have the engineering resources to manage a complex deployment

Choose **OpenMetadata** if:
- You value a clean, collaborative user interface
- Built-in data quality monitoring is a priority
- You want a standardized metadata schema
- You prefer a balance between features and operational simplicity

All three platforms are Apache 2.0 licensed, meaning you can use, modify, and distribute them freely. The best approach is to run each platform's Docker Compose quickstart, ingest metadata from your most critical data source, and evaluate the experience with your actual data. The catalog that feels most intuitive to your team is the right choice.

## Keeping Your Catalog Updated

A data catalog is only useful if its metadata is current. Set up automated ingestion pipelines that run on a schedule:

```bash
# Cron job for daily metadata ingestion
# Add to your crontab: crontab -e
0 2 * * * cd /opt/data-catalog && ./run_ingestion.sh >> /var/log/catalog-ingestion.log 2>&1
```

```bash
#!/bin/bash
# run_ingestion.sh - Daily metadata refresh
#!/bin/bash
set -e

echo "[$(date)] Starting metadata ingestion..."

# Ingest from primary data warehouse
metadata ingest -c warehouse_ingestion.yaml

# Ingest dbt model metadata
metadata ingest -c dbt_ingestion.yaml

# Run data quality profiling
metadata ingest -c data_quality.yaml

echo "[$(date)] Metadata ingestion complete."
```

Monitor ingestion health through the platform's built-in dashboards or by scraping ingestion logs into your existing monitoring stack (Prometheus, Grafana). Set up alerts for failed ingestion runs so metadata gaps are caught early rather than discovered by frustrated analysts.

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
