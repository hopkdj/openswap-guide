---
title: "CloudQuery vs Steampipe vs Cartography: Self-Hosted Cloud Infrastructure Querying 2026"
date: 2026-04-27
tags: ["comparison", "guide", "self-hosted", "cloud", "infrastructure", "security"]
draft: false
description: "Compare CloudQuery, Steampipe, and Cartography for self-hosted cloud infrastructure inventory, querying, and relationship mapping. Complete deployment guide with Docker configs for 2026."
---

Managing cloud infrastructure across AWS, Azure, and GCP becomes increasingly complex as organizations scale. Without a centralized inventory, security teams struggle to answer basic questions: How many S3 buckets are publicly accessible? Which IAM roles have overly permissive policies? What resources are orphaned after a project ends?

Three open-source tools have emerged to solve this problem by letting you query your entire cloud estate using familiar interfaces: SQL and graph databases. **CloudQuery** transforms cloud APIs into SQL-queryable tables, **Steampipe** provides real-time virtual database access, and **Cartography** builds a Neo4j knowledge graph of infrastructure relationships.

This guide compares all three tools in depth, including Docker deployment configs, performance benchmarks, and use-case recommendations.

## Why Self-Hosted Cloud Infrastructure Querying Matters

Cloud provider consoles give you a resource list, but they do not let you:

- **Correlate resources across providers** — finding which EC2 instance connects to which RDS database across accounts
- **Query historical snapshots** — understanding what changed between last week and today
- **Build custom compliance checks** — detecting unencrypted databases, missing tags, or overly permissive security groups
- **Map attack paths** — understanding how a compromised resource could lead to privilege escalation

Self-hosted tools keep your infrastructure metadata within your own network, avoiding data exfiltration to third-party SaaS platforms. This matters for organizations with regulatory requirements (SOC 2, HIPAA, FedRAMP) that restrict where asset inventory data can reside.

## CloudQuery: ETL Pipeline for Cloud Data

[CloudQuery](https://github.com/cloudquery/cloudquery) (6,387 stars, actively maintained) treats cloud APIs as data sources and syncs them into databases you control. It extracts cloud resource configurations, transforms them into normalized schemas, and loads them into PostgreSQL, DuckDB, or other destinations.

### Architecture

CloudQuery operates as an ETL (Extract, Transform, Load) pipeline:

1. **Source plugins** fetch data from AWS, Azure, GCP, GitHub, Okta, and 70+ other APIs
2. **Transform layer** normalizes data into consistent schemas
3. **Destination plugins** write to PostgreSQL, DuckDB, BigQuery, Snowflake, or local files

This architecture means your data is stored locally and queryable at any time, even when offline.

### Docker Deployment

CloudQuery provides official Docker images. Here is a minimal setup with DuckDB as the destination:

```yaml
version: "3.8"
services:
  cloudquery:
    image: ghcr.io/cloudquery/cloudquery:latest
    volumes:
      - ./cq-config:/root/.cq
      - ./output:/output
      - ~/.aws:/root/.aws:ro
    environment:
      - CQ_PROVIDER_AWS_REGION=us-east-1
    command: ["sync", "aws", "--output", "/output"]
```

And a more complete setup with PostgreSQL:

```yaml
version: "3.8"
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: cq
      POSTGRES_PASSWORD: changeme123
      POSTGRES_DB: cloudquery
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  cloudquery:
    image: ghcr.io/cloudquery/cloudquery:latest
    depends_on:
      - postgres
    volumes:
      - ./config:/root/.cq
      - ~/.aws:/root/.aws:ro
    command: ["sync", "aws", "--dsn", "postgres://cq:changeme123@postgres:5432/cloudquery?sslmode=disable"]

volumes:
  pgdata:
```

### Querying Your Data

Once synced, you run standard SQL against your local database:

```sql
-- Find all publicly accessible S3 buckets
SELECT account_id, region, name
FROM aws_s3_buckets
WHERE block_public_acls = false
   OR block_public_policy = false;

-- List EC2 instances without tags
SELECT instance_id, instance_type, state
FROM aws_ec2_instances
WHERE tags = '[]';

-- Find security groups open to 0.0.0.0/0
SELECT group_id, group_name, ip_protocol, from_port, to_port
FROM aws_ec2_security_group_rules
WHERE cidr_ipv4 = '0.0.0.0/0';
```

## Steampipe: Real-Time Cloud Querying via SQL

[Steampipe](https://github.com/turbot/steampipe) (7,796 stars, actively maintained) takes a fundamentally different approach. Instead of syncing data to a database, it creates a **virtual database** using PostgreSQL Foreign Data Wrappers (FDW). When you run a query, Steampipe calls the cloud API in real-time and returns results as if they were in a local table.

### Architecture

Steampipe's FDW-based architecture means:

- **No data storage** — queries hit live APIs, so results are always current
- **Zero sync delay** — no waiting for ETL pipelines to complete
- **Lower disk usage** — no local database required
- **Higher API usage** — each query makes API calls, which may hit rate limits

This makes Steampipe ideal for ad-hoc investigation and interactive exploration, while CloudQuery is better for scheduled compliance checks and historical analysis.

### Docker Deployment

```yaml
version: "3.8"
services:
  steampipe:
    image: turbot/steampipe:latest
    volumes:
      - ~/.aws:/root/.aws:ro
      - ./steampipe-config:/root/.steampipe
    environment:
      - AWS_REGION=us-east-1
    stdin_open: true
    tty: true
    command: ["query"]
```

For a query-ready setup with dashboard support:

```yaml
version: "3.8"
services:
  steampipe:
    image: turbot/steampipe:latest
    volumes:
      - ~/.aws:/root/.aws:ro
      - ./mod:/workspace
    ports:
      - "9193:9193"
    environment:
      - AWS_REGION=us-east-1
    command: ["service", "start"]
```

### Interactive Querying

Steampipe launches an interactive SQL shell connected to your cloud APIs:

```bash
docker run -it --rm \
  -v ~/.aws:/root/.aws:ro \
  turbot/steampipe:latest query
```

```sql
-- Check for public RDS instances (real-time, no sync needed)
SELECT db_instance_identifier, engine, publicly_accessible, multi_az
FROM aws_rds_db_instance
WHERE publicly_accessible = true;

-- Find IAM users without MFA
SELECT user_name, create_date, mfa_active
FROM aws_iam_user
WHERE mfa_active = false;

-- List all Lambda functions with Python 2.7 (deprecated runtime)
SELECT function_name, runtime, last_modified
FROM aws_lambda_function
WHERE runtime LIKE 'python2.7%';
```

### Steampipe Mods

Steampipe's unique "mod" system provides pre-built dashboards and compliance benchmarks:

```bash
# Install the AWS compliance mod
steampipe mod install github.com/turbot/steampipe-mod-aws-compliance

# Run the CIS Level 1 benchmark
steampipe check benchmark.cis_v140
```

## Cartography: Infrastructure Relationship Graph

[Cartography](https://github.com/cartography-cncf/cartography) (3,848 stars, CNCF project, actively maintained) takes a third approach: it ingests cloud resource data into a **Neo4j graph database**, enabling you to explore relationships between resources.

While CloudQuery and Steampipe answer "what resources exist," Cartography answers "how are resources connected?" This is critical for security analysis, where understanding the path from a public-facing asset to a sensitive database reveals attack vectors.

### Architecture

Cartography syncs data from multiple sources (AWS, GCP, Azure, GitHub, Okta, Duo, Jamf) into Neo4j. Each resource becomes a node, and relationships (e.g., `INSTANCE → belongs to → VPC → contains → SUBNET`) become edges.

The graph model enables queries that are difficult or impossible with flat SQL tables:

- Find the shortest path from a public IP to a database
- Identify all resources accessible from a compromised IAM role
- Map the blast radius of a security group rule change

### Docker Compose Deployment

Cartography provides an official `docker-compose.yml` on the `master` branch that deploys both Neo4j and Cartography:

```yaml
version: "3.8"
services:
  neo4j:
    image: neo4j:5.15.0-community
    restart: unless-stopped
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_server_memory_pagecache_size=1G
      - NEO4J_server_memory_heap_initial__size=1G
      - NEO4J_server_memory_heap_max__size=1G
      - NEO4J_AUTH=neo4j/changeme123
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_security_procedures_allowlist=apoc.*
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*

  cartography:
    image: ghcr.io/cartography-cncf/cartography:latest
    platform: linux/x86_64
    restart: on-failure
    depends_on:
      - neo4j
    volumes:
      - ~/.aws:/var/cartography/.aws/:ro
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_PASSWORD=changeme123
    command: ["-v", "--neo4j-uri=bolt://neo4j:7687", "--aws-sync-all-profiles"]
```

### Querying the Graph

Cartography uses Cypher, Neo4j's graph query language:

```cypher
// Find all EC2 instances in public subnets
MATCH (i:EC2Instance)-[:NETWORK_INTERFACE]->(eni:NetworkInterface)
      -[:SUBNET]->(s:Subnet)-[:ROUTE_TABLE]->(rt:RouteTable)
      -[:ROUTE]->(r:Route {destination_cidr_block: "0.0.0.0/0"})
RETURN i.id, i.instance_type, s.id;

// Find S3 buckets accessible from a specific IAM role
MATCH (role:IAMRole {name: "AdminRole"})
      -[:STS_ASSUME_ROLE]->(assumed:IAMRole)
      -[:POLICY]->(policy:IAMPolicy)
      -[:APPLIES_TO]->(bucket:S3Bucket)
RETURN bucket.name, bucket.region, bucket.public_access;

// Find the attack path from internet to database
MATCH path = shortestPath(
  (internet:InternetGateway)-[*]->(db:RDSInstance)
)
RETURN path;
```

### Neo4j Browser Access

Access the Neo4j Browser at `http://localhost:7474` to visually explore your infrastructure graph. Nodes are color-coded by resource type, and edges show relationships. This visual exploration is impossible with flat SQL databases.

## Comparison Table

| Feature | CloudQuery | Steampipe | Cartography |
|---------|-----------|-----------|-------------|
| **Query Language** | SQL | SQL | Cypher (graph) |
| **Data Model** | Relational tables | Virtual tables (FDW) | Graph (Neo4j) |
| **Data Storage** | PostgreSQL, DuckDB, etc. | None (real-time API) | Neo4j database |
| **Multi-Cloud** | AWS, Azure, GCP, 70+ sources | AWS, Azure, GCP, SaaS | AWS, GCP, Azure, GitHub, Okta |
| **Sync Required** | Yes (ETL pipeline) | No (real-time) | Yes (graph import) |
| **Relationship Queries** | Via JOINs | Via JOINs | Native (graph traversal) |
| **Dashboard** | Yes (CloudQuery UI) | Yes (Steampipe dashboards) | Neo4j Browser |
| **Compliance Checks** | SQL-based | Built-in mods (CIS, NIST) | Custom Cypher queries |
| **Docker Image** | `ghcr.io/cloudquery/cloudquery` | `turbot/steampipe` | `ghcr.io/cartography-cncf/cartography` |
| **GitHub Stars** | 6,387 | 7,796 | 3,848 |
| **Language** | Go | Go | Python |
| **Best For** | Scheduled audits, historical data | Ad-hoc exploration, live queries | Security analysis, relationship mapping |

## Performance and Cost Considerations

### Sync Speed

CloudQuery and Cartography must sync all resources before querying. For a typical AWS account with ~5,000 resources:

- **CloudQuery**: 2-5 minutes for full sync to PostgreSQL
- **Cartography**: 3-8 minutes for full sync to Neo4j
- **Steampipe**: Instant (but each query makes API calls)

### API Rate Limits

Steampipe's real-time approach means every query hits cloud APIs. For large organizations, this can trigger rate limiting. CloudQuery and Cartography mitigate this by batching syncs during off-peak hours.

### Storage Requirements

- **CloudQuery + PostgreSQL**: ~500MB-2GB per cloud account (depends on resource count)
- **Cartography + Neo4j**: ~1-5GB per cloud account (graph storage is larger due to relationship edges)
- **Steampipe**: Near zero (no local storage)

## Choosing the Right Tool

### Use CloudQuery When

- You need **scheduled compliance reports** that run automatically
- You want **historical data** for trend analysis and change tracking
- You prefer **SQL** and already have a PostgreSQL or DuckDB setup
- You need to sync from **70+ sources** beyond just cloud providers

### Use Steampipe When

- You need **instant answers** without waiting for sync jobs
- You want **interactive exploration** of your infrastructure
- You value **pre-built compliance mods** (CIS, NIST, PCI-DSS)
- Your team is small enough that API rate limits are not a concern

### Use Cartography When

- You need to **understand relationships** between resources
- You are performing **security analysis** or threat modeling
- You want to **visualize your infrastructure** as a graph
- You need to answer "what happens if this resource is compromised?"

For most organizations, the ideal setup combines **CloudQuery for scheduled audits** and **Cartography for security analysis**. Steampipe serves as a complementary tool for quick, ad-hoc queries.

## Installation Commands

### CloudQuery (Linux/macOS)

```bash
curl -L https://github.com/cloudquery/cloudquery/releases/latest/download/cloudquery_linux_amd64 \
  -o cloudquery
chmod +x cloudquery
sudo mv cloudquery /usr/local/bin/
cloudquery init aws
```

### Steampipe (Linux/macOS)

```bash
sudo /bin/sh -c "$(curl -fsSL https://steampipe.io/install/steampipe.sh)" -- --stable
steampipe plugin install aws
```

### Cartography (Python/pip)

```bash
pip3 install cartography
cartography --neo4j-uri bolt://localhost:7687 --aws-sync-all-profiles
```

For related reading, see our [cloud security audit guide with Prowler vs Scout Suite](../prowler-vs-scout-suite-vs-cloud-custodian-self-hosted-cloud-security-audit-guide-2026/) and [container image scanning with Trivy vs Grype](../self-hosted-container-image-scanning-trivy-grype-clair-anchore-guide-2026/).

## FAQ

### What is the difference between CloudQuery and Steampipe?

CloudQuery uses an ETL pipeline to sync cloud data into a local database (PostgreSQL or DuckDB), enabling scheduled queries and historical analysis. Steampipe uses PostgreSQL Foreign Data Wrappers to query cloud APIs in real-time without storing any data locally. CloudQuery is better for compliance automation; Steampipe is better for interactive exploration.

### Can I use Cartography without Neo4j?

No. Cartography is built specifically for Neo4j and uses Cypher queries. The graph database is core to its value proposition — relationship mapping and attack path analysis require a graph data model. However, Neo4j Community Edition is free and open-source, so there is no licensing cost.

### Do these tools support Azure and GCP in addition to AWS?

Yes. All three tools support AWS, Azure, and GCP. CloudQuery has the broadest support with 70+ source plugins including GitHub, Okta, Kubernetes, and Terraform Cloud. Steampipe has plugins for AWS, Azure, GCP, Slack, Jira, and more. Cartography supports AWS, GCP, Azure, GitHub, Okta, Duo, and Jamf.

### How often should I sync cloud infrastructure data?

For CloudQuery and Cartography, daily syncs are recommended for most organizations. High-security environments may benefit from hourly syncs. Steampipe does not require syncing since it queries APIs in real-time, but frequent interactive queries may hit cloud provider rate limits.

### Are these tools free to use?

Yes, all three are open-source and free. CloudQuery is Apache 2.0 licensed, Steampipe is Apache 2.0, and Cartography is Apache 2.0 under the CNCF. All costs are limited to the infrastructure required to run the databases (PostgreSQL, Neo4j) and the cloud API calls themselves.

### Can I run these tools on-premises without cloud access?

CloudQuery and Cartography require initial cloud access to sync data. Once synced, you can query the local database without cloud connectivity. Steampipe requires ongoing cloud API access for every query since it does not store data locally.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "CloudQuery vs Steampipe vs Cartography: Self-Hosted Cloud Infrastructure Querying 2026",
  "description": "Compare CloudQuery, Steampipe, and Cartography for self-hosted cloud infrastructure inventory, querying, and relationship mapping. Complete deployment guide with Docker configs for 2026.",
  "datePublished": "2026-04-27",
  "dateModified": "2026-04-27",
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
