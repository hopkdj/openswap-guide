---
title: "Self-Hosted Elasticsearch Management UIs: Cerebro vs ElasticHQ vs Dejavu"
date: "2026-05-11"
tags: ["elasticsearch", "database-management", "monitoring", "open-source", "self-hosted"]
draft: false
---

Managing an Elasticsearch cluster requires more than just API calls and curl commands. Whether you are running a single-node development cluster or a multi-node production deployment, having a visual interface to monitor cluster health, manage indices, and execute queries is essential. This guide compares three popular open-source Elasticsearch management UIs: Cerebro, ElasticHQ, and Dejavu.

## What Is an Elasticsearch Management UI?

Elasticsearch is a distributed search and analytics engine built on Apache Lucene. While it exposes a comprehensive REST API, managing clusters at scale demands tools that provide visual cluster topology maps, index lifecycle management, query builders, and real-time health monitoring. Management UIs fill this gap by wrapping the Elasticsearch API in an intuitive web interface.

All three tools covered here are self-hosted, open-source, and support multiple Elasticsearch versions. They can be deployed via Docker Compose alongside your cluster, making them easy to integrate into existing infrastructure.

## Comparison Overview

| Feature | Cerebro | ElasticHQ | Dejavu |
|---------|---------|-----------|--------|
| GitHub Stars | 5,617 | 5,005 | 8,462 |
| Last Updated | Feb 2024 | Jan 2024 | Feb 2026 |
| Language | Scala/Play | Python/Flask | JavaScript/React |
| Multi-Cluster | Yes | Yes | Yes |
| Query Builder | Basic REST console | Advanced with templates | Rich query DSL UI |
| Index Management | Full CRUD | Full CRUD | Full CRUD |
| Cluster Health | Visual topology map | Dashboard with metrics | Status indicators |
| Authentication | LDAP, Basic Auth | Basic Auth, OAuth | None built-in |
| Docker Image | Official on Docker Hub | Community images | Official on Docker Hub |
| REST API Console | Yes | Yes | Yes |
| Backup/Snapshot UI | Yes | Yes | No |
| OpenSearch Support | Limited | Yes | Yes |

## Cerebro

Cerebro is a Scala-based web application built on the Play Framework. Originally forked from the Elasticsearch Kopf plugin, it has evolved into a standalone cluster management tool with strong multi-cluster support and LDAP authentication.

**Key features:**
- Visual cluster topology with node allocation details
- REST API console with syntax highlighting
- Index creation, deletion, and alias management
- Snapshot and repository management UI
- LDAP and basic authentication support
- Shard allocation visualization

**Strengths:** Cerebro excels at cluster-level operations. Its visual node map shows shard distribution across nodes, making it easy to identify imbalanced clusters. LDAP integration makes it suitable for enterprise deployments.

**Weaknesses:** The project has seen reduced update frequency (last commit Feb 2024). The query builder is basic compared to Dejavu. The UI is functional but less polished than modern alternatives.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  cerebro:
    image: lmenezes/cerebro:0.9.4
    container_name: cerebro
    ports:
      - "9000:9000"
    volumes:
      - ./application.conf:/opt/cerebro/conf/application.conf:ro
    restart: unless-stopped
```

Configuration file (`application.conf`):
```hocon
hosts = [
  {
    host = "http://elasticsearch:9200"
    name = "production-cluster"
    auth = {
      type = "basic"
      username = "elastic"
      password = "${ES_PASSWORD}"
    }
  }
]
```

## ElasticHQ

ElasticHQ is a Python-based management application using Flask. It provides a clean dashboard interface with comprehensive cluster monitoring, index management, and a powerful query builder with template support.

**Key features:**
- Real-time cluster health dashboard
- Index CRUD operations with mapping visualization
- Advanced query builder with saved templates
- REST API explorer
- Basic authentication and OAuth support
- OpenSearch compatibility

**Strengths:** ElasticHQ has the most polished dashboard of the three tools. Its query template system lets you save and reuse common queries. The cluster overview page shows node status, index sizes, and shard health at a glance.

**Weaknesses:** Like Cerebro, update frequency has slowed (last commit Jan 2024). No official Docker image — you need to build from source or use community images. Authentication options are limited compared to Cerebro.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  elastichq:
    image: elastichq/elasticsearch-hq:release-v3.5.14
    container_name: elastichq
    ports:
      - "5000:5000"
    environment:
      - HQ_DEFAULT_URL=http://elasticsearch:9200
    restart: unless-stopped
```

## Dejavu

Dejavu is a JavaScript-based web UI built with React. Developed by appbase.io, it focuses on data browsing and search capabilities with a modern, responsive interface. It supports both Elasticsearch and OpenSearch.

**Key features:**
- Rich data browser with faceted search
- Import/export data in JSON, CSV formats
- Visual query builder with auto-complete
- Reference search UI generator
- Real-time data editing
- OpenSearch support

**Strengths:** Dejavu has the most modern UI and the most active development (last commit Feb 2026, 8,462 stars). Its data import/export capabilities are unmatched — you can bulk load CSV or JSON data directly through the browser. The reference search UI feature lets you generate a ready-to-use search interface for your indices.

**Weaknesses:** No built-in authentication — you must place it behind a reverse proxy with auth. Limited cluster management features compared to Cerebro (no snapshot management, no shard allocation visualization).

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  dejavu:
    image: appbaseio/dejavu:3.6.0
    container_name: dejavu
    ports:
      - "1358:1358"
    environment:
      - ES_CLUSTER_URL=http://elasticsearch:9200
    restart: unless-stopped
```

## Choosing the Right Elasticsearch Management UI

**Use Cerebro when:** You need LDAP authentication, cluster topology visualization, and snapshot management. It is the best choice for DevOps teams managing multi-cluster Elasticsearch deployments in production environments.

**Use ElasticHQ when:** You want a polished dashboard with query templates and strong cluster monitoring. It is ideal for developers who need to run saved queries and monitor cluster health from a single screen.

**Use Dejavu when:** Your primary need is data browsing, import/export, and a modern search interface. It excels for data teams who work directly with index content and need to quickly search, filter, and modify documents.

For comprehensive cluster operations, many teams run Cerebro alongside Dejavu — using Cerebro for infrastructure management and Dejavu for data-level operations.

## Why Self-Host Your Elasticsearch Management UI?

Running your own Elasticsearch management interface gives you full control over access, data visibility, and tooling customization. Cloud-hosted alternatives like Kibana Cloud or Elastic Cloud impose usage limits, restrict plugin installations, and add per-node licensing costs that grow with your cluster size.

Self-hosted management UIs connect directly to your Elasticsearch cluster without routing traffic through third-party infrastructure. This means your query patterns, index structures, and cluster topology data never leave your network. For organizations handling sensitive data — financial records, healthcare information, or personal identifiable information — this data locality is a compliance requirement.

The tools covered here all run as lightweight containers. Cerebro uses approximately 256MB of RAM, ElasticHQ runs on under 128MB, and Dejavu is a static single-page application served by a minimal Node.js process. The resource overhead is negligible compared to the Elasticsearch nodes they manage.

For related reading, see our [Elasticsearch vs OpenSearch vs Typesense comparison](../2026-04-16-elasticsearch-vs-opensearch-vs-typesense-self-hosted-search-guide/) and [log retention lifecycle management guide](../2026-05-06-self-hosted-log-retention-lifecycle-management-elasticsearch-ilm-loki-opensearch-ism/). If you are building a complete observability stack, our [log shipping comparison](../self-hosted-log-shipping-vector-fluentbit-logstash-guide-2026/) covers data ingestion options.


Running Elasticsearch management tools alongside your cluster also eliminates the network latency introduced by cloud-hosted alternatives. When managing clusters with hundreds of indices and millions of documents, every millisecond of query latency matters. Local management tools communicate with your Elasticsearch nodes over the internal network, avoiding the round-trip delays of cloud dashboards.

For teams running Elasticsearch clusters across multiple data centers, self-hosted management UIs can be deployed in each location, providing local access without cross-datacenter network dependencies. This distributed approach improves both performance and resilience — if one data center loses connectivity, the local management interface remains available for operations teams.

## FAQ

### Can Cerebro connect to multiple Elasticsearch clusters?

Yes, Cerebro supports multiple cluster connections defined in its configuration file. Each cluster entry specifies the host URL, name, and authentication method. You can switch between clusters from the UI dropdown.

### Does ElasticHQ support OpenSearch?

Yes, ElasticHQ is compatible with OpenSearch. The REST API between Elasticsearch 7.x and OpenSearch 1.x/2.x is largely compatible, and ElasticHQ works with both.

### Is Dejavu free and open-source?

Yes, Dejavu is released under the MIT license. It is free to use for both personal and commercial projects. The source code is available on GitHub at appbaseio/dejavu.

### How do I add authentication to Dejavu?

Dejavu does not have built-in authentication. You should place it behind a reverse proxy (Nginx, Traefik, or Caddy) with basic auth, OAuth, or JWT authentication. Alternatively, use your Elasticsearch cluster's built-in security features to restrict index access.

### Can I use these tools with Elasticsearch 8.x?

Cerebro 0.9.4 supports Elasticsearch 7.x and 8.x. ElasticHQ works with Elasticsearch 6.x through 8.x. Dejavu supports Elasticsearch 5.x through 8.x and OpenSearch 1.x/2.x.

### What ports do these services use?

Cerebro uses port 9000, ElasticHQ uses port 5000, and Dejavu uses port 1358. All ports are configurable and can be remapped in your Docker Compose file.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Elasticsearch Management UIs: Cerebro vs ElasticHQ vs Dejavu",
  "description": "Compare Cerebro, ElasticHQ, and Dejavu — three open-source web UIs for managing Elasticsearch clusters. Self-hosted with Docker Compose, cluster health monitoring, and query management.",
  "datePublished": "2026-05-11",
  "dateModified": "2026-05-11",
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

