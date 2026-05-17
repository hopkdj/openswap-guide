---
title: "Self-Hosted Log and Metrics Dashboards: OpenSearch Dashboards vs Grafana vs Kibana OSS"
date: "2026-05-17"
tags: ["monitoring", "dashboards", "visualization", "opensearch", "grafana", "kibana", "observability", "self-hosted"]
draft: false
---

When you collect logs, metrics, and traces across your infrastructure, the data is only useful if you can see it. Visualization dashboards transform raw telemetry into actionable insights — showing you CPU spikes, error rate trends, slow query patterns, and security anomalies at a glance.

Three open-source platforms dominate the self-hosted dashboard space for log and metrics visualization: **OpenSearch Dashboards**, **Grafana**, and **Kibana OSS**. Each offers a different approach to turning data into dashboards.

This guide compares all three — their data source support, visualization capabilities, deployment options, and which scenarios each handles best.

## What Is a Log and Metrics Dashboard?

A visualization dashboard connects to data backends (Elasticsearch, Prometheus, Loki, OpenSearch) and presents the data through charts, graphs, tables, and alert panels. Key capabilities include:

- **Time-series visualization** — line charts, area charts, and heatmaps showing trends over time
- **Log exploration** — searchable, filterable log viewer with field highlighting
- **Dashboard composition** — arrange multiple visualizations into a single monitoring view
- **Alerting** — notify teams when metrics cross thresholds or anomaly patterns emerge
- **Multi-tenant views** — different dashboards for different teams or services
- **Saved searches and queries** — reusable query definitions with custom filters

## OpenSearch Dashboards: The Open-Source Kibana Fork

OpenSearch Dashboards is the visualization component of the OpenSearch suite, forked from Kibana 7.10.2 after Elastic changed the licensing of newer Kibana versions. It provides the familiar Kibana experience with an open-source license (Apache 2.0) and active development by AWS and the open-source community.

**Key characteristics:**

- **Familiar Kibana UI** — near-identical interface to Kibana 7.10, minimal learning curve
- **Tight OpenSearch integration** — optimized for OpenSearch data sources with full feature support
- **Security plugin** — built-in authentication, role-based access control, and audit logging
- **Alerting and notifications** — configurable alert rules with multiple notification channels
- **ML anomaly detection** — integrated machine learning for identifying unusual patterns in data
- **Plugin ecosystem** — extensible via OpenSearch Dashboards plugins

### Docker Deployment

```yaml
version: '3'
services:
  opensearch:
    image: opensearchproject/opensearch:2.15.0
    environment:
      - discovery.type=single-node
      - OPENSEARCH_INITIAL_ADMIN_PASSWORD=Str0ngP@ssw0rd
      - "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - os_data:/usr/share/opensearch/data
    ports:
      - "9200:9200"

  opensearch-dashboards:
    image: opensearchproject/opensearch-dashboards:2.15.0
    ports:
      - "5601:5601"
    environment:
      OPENSEARCH_HOSTS: '["https://opensearch:9200"]'
    depends_on:
      - opensearch
```

### OpenSearch Dashboards Features

The dashboard provides:

- **Discover** — interactive log exploration with field-based filtering and Lucene query syntax
- **Visualize** — create individual charts, tables, and maps from your data
- **Dashboard** — compose multiple visualizations into a unified monitoring view
- **Dev Tools** — console for running OpenSearch API queries directly
- **Security** — user management, roles, and tenant-based data isolation
- **Alerting** — visual alert rule builder with threshold, anomaly, and frequency-based triggers

## Grafana: The Universal Observability Dashboard

Grafana is the most popular open-source visualization platform, supporting dozens of data sources beyond just log and metrics backends. While it started as a metrics dashboard tool (primarily for Graphite and Prometheus), it has evolved into a unified observability platform that handles logs, traces, profiles, and more.

**Key characteristics:**

- **Multi-source dashboards** — single dashboard can pull from Prometheus, Loki, Elasticsearch, MySQL, PostgreSQL, and 100+ other data sources
- **Rich visualization library** — time series, stat panels, heatmaps, geo maps, histograms, state timelines
- **Dashboard-as-code** — export dashboards as JSON for version control and reproducibility
- **Alerting** — unified alerting system with multi-channel notifications (Slack, PagerDuty, email, webhooks)
- **Plugins** — extensive plugin ecosystem for additional visualizations and data sources
- **Enterprise features** — SSO, RBAC, reporting, and team management (open-source core + paid add-ons)

### Docker Deployment

```yaml
version: '3'
services:
  grafana:
    image: grafana/grafana:11.3.0
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_INSTALL_PLUGINS=grafana-piechart-panel
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
```

### Provisioning Data Sources

Grafana supports provisioning data sources from configuration files:

```yaml
# grafana/provisioning/datasources/datasources.yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
  - name: Elasticsearch
    type: elasticsearch
    access: proxy
    url: http://elasticsearch:9200
    database: "[logs-]YYYY.MM.DD"
```

### Building Dashboards with Grafana

Grafana's panel editor supports:

- **PromQL** for Prometheus metrics — complex aggregations, rate calculations, histogram quantiles
- **LogQL** for Loki logs — filter, parse, and aggregate log data with a dedicated query language
- **Lucene/KQL** for Elasticsearch/OpenSearch — full-text search and field-based filtering
- **SQL** for relational databases — direct SQL queries against MySQL, PostgreSQL, and others

A single Grafana dashboard can show Prometheus CPU metrics, Loki error logs, and Elasticsearch application logs side by side — all in one view.

## Kibana OSS: The Original Elasticsearch Dashboard

Kibana OSS (Open Source Software) is the last freely available version of Kibana under the Apache 2.0 license (version 7.10.2). Newer versions of Kibana use the SSPL license, which many organizations consider non-open-source. Kibana OSS remains functional for basic Elasticsearch visualization but lacks the latest features.

**Key characteristics:**

- **Native Elasticsearch integration** — purpose-built for Elasticsearch data
- **Timelion** — time-series expression language for complex metric visualizations
- **Canvas** — pixel-perfect reporting and presentation-style dashboards
- **Vega** — custom visualization using the Vega grammar
- **Machine Learning** — anomaly detection and forecasting (limited in OSS version)
- **Limited updates** — frozen at 7.10.2; no new features or security patches

### Docker Deployment

```yaml
version: '3'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch-oss:7.10.2
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"

  kibana:
    image: docker.elastic.co/kibana/kibana-oss:7.10.2
    ports:
      - "5601:5601"
    environment:
      ELASTICSEARCH_HOSTS: '["http://elasticsearch:9200"]'
    depends_on:
      - elasticsearch
```

### Why Choose Kibana OSS

Kibana OSS is a reasonable choice when:

- You are already running **Elasticsearch 7.x** and need a compatible dashboard
- You require **no new features** — the 7.10.2 feature set is sufficient
- You want the **most polished Elasticsearch-specific dashboard** experience
- Your organization has an **existing Kibana skill set** and wants minimal retraining

## Comparison Table

| Feature | OpenSearch Dashboards | Grafana | Kibana OSS |
|---------|----------------------|---------|------------|
| **License** | Apache 2.0 | AGPL 3.0 | Apache 2.0 |
| **Version** | 2.x (actively developed) | 11.x (actively developed) | 7.10.2 (frozen) |
| **Primary Data Source** | OpenSearch | 100+ data sources | Elasticsearch |
| **Log Exploration** | Discover (Lucene/KQL) | Explore Logs (LogQL) | Discover (Lucene) |
| **Metrics Visualization** | Via OpenSearch aggregations | PromQL, LogQL, SQL | Timelion, Vega |
| **Multi-Source Dashboards** | No (OpenSearch only) | Yes (100+ sources) | No (Elasticsearch only) |
| **Alerting** | Built-in (OpenSearch) | Unified Alerting | Limited (Watcher not in OSS) |
| **ML/Anomaly Detection** | Yes (OpenSearch ML) | Via plugins | Limited in OSS |
| **Dashboard Sharing** | Saved objects, reporting | Share panel, PDF export | Saved objects |
| **Security/RBAC** | Built-in security plugin | Enterprise feature | None in OSS |
| **Plugin Ecosystem** | Moderate | Extensive | Limited (frozen version) |
| **Development Status** | Active (AWS + community) | Active (Grafana Labs) | Frozen (no updates) |
| **Docker Image Size** | ~600MB | ~400MB | ~800MB |
| **Resource Requirements** | ~1GB RAM | ~256MB RAM | ~512MB RAM |

## When to Choose Each

### Choose OpenSearch Dashboards when:

- You are running or planning to run **OpenSearch** as your primary data store
- You need **active development** with regular security patches and feature updates
- You want the **familiar Kibana experience** without SSPL licensing concerns
- You need **built-in security** — authentication, authorization, and audit logging
- Your team wants **ML-powered anomaly detection** integrated into the dashboard

### Choose Grafana when:

- You have **multiple data sources** — Prometheus, Loki, Elasticsearch, databases, cloud APIs
- You want a **single dashboard platform** for all your observability needs
- You need the **richest visualization library** — the most chart types and panel options
- You prefer **dashboard-as-code** — JSON exports for Git version control and CI/CD
- You want **unified alerting** across all data sources in one notification system
- Your team values a **large, active community** with extensive tutorials and plugins

### Choose Kibana OSS when:

- You are locked into **Elasticsearch 7.x** and cannot migrate to OpenSearch
- You need the **most polished Elasticsearch-specific** visualization experience
- Your use case is **fully covered** by the 7.10.2 feature set
- You have **existing Kibana dashboards** and want zero migration effort

## Why Self-Host Your Observability Dashboards?

Observability dashboards contain your infrastructure's most sensitive operational data — error patterns, performance bottlenecks, security events, and user activity. Self-hosting ensures this data never leaves your control.

Grafana and OpenSearch Dashboards both run efficiently on modest hardware. A single VM with 4GB RAM can host a complete Grafana + Loki + Prometheus stack, providing enterprise-grade observability at a fraction of the cost of hosted alternatives like Datadog or New Relic.

For teams building complete observability stacks, our [Grafana Loki vs Mimir vs Tempo comparison](../2026-05-14-grafana-observability-stack-loki-mimir-tempo-guide/) covers the data collection layer. And if you're managing Elasticsearch clusters, the [Cerebro vs ElasticHQ vs Dejavu guide](/) covers cluster administration tools. For log retention and lifecycle management, our [Elasticsearch ILM vs Loki vs OpenSearch ISM article](../2026-05-06-self-hosted-log-retention-lifecycle-management-elasticsearch-ilm-loki-opensearch-ism-guide/) covers storage optimization.

## FAQ

### Can Grafana connect to OpenSearch?

Yes. Grafana supports OpenSearch as a data source through its built-in OpenSearch plugin. You can create Log Explorer panels (equivalent to OpenSearch Discover), build metric visualizations using OpenSearch aggregations, and set up alerts based on OpenSearch data — all within Grafana's interface.

### Is Kibana OSS still receiving security updates?

No. Kibana OSS is frozen at version 7.10.2 and receives no new features or security patches from Elastic. Organizations requiring security updates should either migrate to OpenSearch Dashboards or use a newer Kibana version under the SSPL license.

### Can I run Grafana and OpenSearch Dashboards side by side?

Yes. Many organizations run both: OpenSearch Dashboards for log exploration and search (the Discover interface), and Grafana for metrics dashboards and cross-source visualization. They can both connect to the same OpenSearch/Elasticsearch backend without conflict.

### Does Grafana support log management like Kibana's Discover?

Grafana's "Explore Logs" feature (using LogQL with Loki) provides log exploration similar to Kibana Discover. When connected to Elasticsearch or OpenSearch, Grafana can also perform Lucene/KQL queries for full-text log search. However, the log exploration experience is not as deeply integrated as Kibana/OpenSearch Discover, which offers field discovery, histogram views, and saved searches out of the box.

### Which dashboard tool uses the least resources?

Grafana has the lightest resource footprint — it can run on 256MB RAM since it is primarily a visualization layer that queries external data sources. OpenSearch Dashboards requires ~1GB RAM as it runs a full Node.js application server. Kibana OSS needs ~512MB RAM but is paired with Elasticsearch which requires significantly more.

### Can I migrate Kibana dashboards to Grafana?

There is no direct migration path, as Kibana saves dashboards in Elasticsearch's format while Grafana uses its own JSON structure. However, community tools like `kibana2grafana` can convert basic Kibana visualizations to Grafana panels. For complex dashboards, manual recreation in Grafana's panel editor is often necessary.

## Choosing the Right Visualization Dashboard

For most self-hosted observability setups, **Grafana** is the best choice — its multi-source support, rich visualization library, and dashboard-as-code capabilities make it the most versatile option. If you are running OpenSearch and need the tightest integration with your search backend, **OpenSearch Dashboards** provides the best experience. **Kibana OSS** is only recommended for organizations locked into Elasticsearch 7.x that cannot migrate to OpenSearch.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Log and Metrics Dashboards: OpenSearch Dashboards vs Grafana vs Kibana OSS",
  "description": "Compare OpenSearch Dashboards, Grafana, and Kibana OSS for self-hosted log and metrics visualization. Includes Docker deployment, features comparison, and decision guide.",
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
