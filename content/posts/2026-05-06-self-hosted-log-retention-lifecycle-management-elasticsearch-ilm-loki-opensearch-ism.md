---
title: "Self-Hosted Log Retention & Lifecycle Management: Elasticsearch ILM vs Loki Retention vs OpenSearch ISM"
date: "2026-05-06"
tags: ["logging", "elasticsearch", "loki", "opensearch", "data-retention", "lifecycle-management", "ilm", "storage-optimization"]
draft: false
---

Managing log retention is one of the most critical operational challenges for any self-hosted observability stack. Without proper lifecycle management, log indices grow unbounded, storage costs explode, and query performance degrades. Index Lifecycle Management (ILM), retention policies, and Index State Management (ISM) are the mechanisms that automate the movement, sizing, and deletion of log data across its useful lifetime.

This guide compares the three most widely used self-hosted log retention systems: **Elasticsearch Index Lifecycle Management (ILM)**, **Grafana Loki's native retention model**, and **OpenSearch Index State Management (ISM)**. Each takes a fundamentally different approach to log lifecycle management, and the right choice depends on your data volume, query patterns, and storage budget.

## Understanding Log Lifecycle Management

Log data follows a predictable access pattern: recent logs are queried frequently for debugging and alerting, older logs are accessed occasionally for compliance or incident forensics, and very old logs are rarely needed but may be required for audit purposes. A good retention system moves data through these stages automatically, reducing storage costs while keeping data accessible for as long as it matters.

The typical lifecycle has three phases:

1. **Hot phase** — Active indexing, fast queries, stored on fast storage (SSD/NVMe)
2. **Warm phase** — Read-only, slower queries, moved to cheaper storage (HDD/S3)
3. **Delete phase** — Data is permanently removed when it exceeds the retention period

Each log backend implements this lifecycle differently. Elasticsearch uses ILM policies with named phases, Loki uses per-tenant retention periods with configurable storage tiers, and OpenSearch uses ISM policies that can be attached to index templates.

## Elasticsearch Index Lifecycle Management (ILM)

Elasticsearch ILM is the most feature-rich retention system of the three. It was introduced in Elasticsearch 6.6 and has evolved through multiple versions with support for searchable snapshots, cross-cluster replication, and data tier architecture.

### How ILM Works

ILM policies define actions that are triggered at specific phases of an index's lifecycle. Each phase can include multiple actions:

- **Hot phase**: rollover (create new index when size/age threshold is reached), shrink, forcemerge
- **Warm phase**: allocate (move to warm nodes), set priority, readonly
- **Cold phase**: searchable snapshot (move to object storage), allocate
- **Delete phase**: delete (permanently remove the index)

The rollover action is the foundation of ILM. It creates a new write index when the current one exceeds a maximum size or age, ensuring that individual indices stay within manageable bounds.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.15.0
    container_name: elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms1g -Xmx1g
    ports:
      - "9200:9200"
    volumes:
      - es-data:/usr/share/elasticsearch/data
    ulimits:
      memlock:
        soft: -1
        hard: -1

  kibana:
    image: docker.elastic.co/kibana/kibana:8.15.0
    container_name: kibana
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

volumes:
  es-data:
```

### ILM Policy Configuration

An ILM policy is defined via the Elasticsearch REST API. Here is a typical log retention policy:

```json
PUT _ilm/policy/logs-lifecycle
{
  "policy": {
    "phases": {
      "hot": {
        "min_age": "0ms",
        "actions": {
          "rollover": {
            "max_size": "50gb",
            "max_age": "7d"
          },
          "set_priority": {
            "priority": 100
          }
        }
      },
      "warm": {
        "min_age": "7d",
        "actions": {
          "forcemerge": {
            "max_num_segments": 1
          },
          "shrink": {
            "number_of_shards": 1
          },
          "allocate": {
            "number_of_replicas": 0
          },
          "set_priority": {
            "priority": 50
          }
        }
      },
      "cold": {
        "min_age": "30d",
        "actions": {
          "allocate": {
            "number_of_replicas": 0
          },
          "set_priority": {
            "priority": 0
          }
        }
      },
      "delete": {
        "min_age": "90d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
```

This policy rolls over indices at 50GB or 7 days, forcemerges and shrinks warm indices, moves cold indices to cheaper nodes, and deletes everything older than 90 days.

### Strengths

- Granular per-phase control with multiple actions per phase
- Searchable snapshots move cold data to S3 while keeping it queryable
- Data tier architecture (hot/warm/cold/frozen) maps cleanly to ILM phases
- Integration with Kibana for visual policy management
- Rollover-based indexing prevents oversized indices

### Limitations

- ILM requires careful index template configuration to attach policies
- Searchable snapshots require a separate snapshot repository (S3, GCS, Azure)
- Complex policies can be difficult to debug when phases stall
- Resource-intensive for very large deployments (many small indices)

## Grafana Loki Retention Model

Loki takes a fundamentally different approach to log storage. Instead of full-text indexing like Elasticsearch, Loki indexes only labels and stores compressed log chunks. This makes retention simpler but less granular.

### How Loki Retention Works

Loki's retention model is based on a single retention period per tenant (or globally). When the retention period expires, entire chunks are deleted from the underlying object storage. Unlike Elasticsearch's phased lifecycle, Loki does not have built-in hot/warm/cold tiering — but it achieves cost savings through its storage architecture:

- **Index storage** (BoltDB-shipper or TSDB) — stored on local disk or object storage
- **Chunk storage** — compressed log data stored on object storage (S3, GCS, MinIO)
- **Compaction** — background process that merges small chunks and removes deleted data

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  loki:
    image: grafana/loki:3.2.0
    container_name: loki
    command: -config.file=/etc/loki/local-config.yaml
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yaml:/etc/loki/local-config.yaml
      - loki-data:/loki

  promtail:
    image: grafana/promtail:3.2.0
    container_name: promtail
    volumes:
      - /var/log:/var/log
      - ./promtail-config.yaml:/etc/promtail/config.yaml
    command: -config.file=/etc/promtail/config.yaml

volumes:
  loki-data:
```

### Loki Retention Configuration

```yaml
# loki-config.yaml
auth_enabled: false

server:
  http_listen_port: 3100

common:
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: "2024-01-01"
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h

limits_config:
  retention_period: 744h  # 31 days
  allow_structured_metadata: true
  volume_enabled: true

compactor:
  working_directory: /loki/compactor
  compaction_interval: 10m
  retention_enabled: true
  delete_request_store: filesystem
```

The key settings are `limits_config.retention_period` (in hours) and `compactor.retention_enabled` which must be set to true for automatic deletion to work. Without the compactor running with retention enabled, expired data is never cleaned up.

### Strengths

- Simple configuration — single retention period per tenant
- Object storage native — chunks are stored on S3/MinIO by default
- Low storage cost due to label-only indexing and compression
- Multi-tenant support with per-tenant retention periods
- Integration with Grafana for log exploration

### Limitations

- No phased lifecycle (no hot/warm/cold tiers)
- Deletion is eventually consistent — compactor must run first
- Limited granularity — retention is all-or-nothing per tenant
- No rollover mechanism — chunk sizes are managed automatically
- Full-text search is slower than Elasticsearch for large datasets

## OpenSearch Index State Management (ISM)

OpenSearch ISM is the fork-based successor to Elasticsearch ILM, developed by AWS after the Elasticsearch license change. It adds several features on top of the original ILM model, including notifications, custom conditions, and a more flexible action system.

### How ISM Works

ISM operates on the same index lifecycle concept as ILM but with additional capabilities:

- **States** — similar to ILM phases but with more flexibility in transitions
- **Actions** — rollover, replica_count, index_priority, force_merge, shrink, snapshot, delete, and more
- **Transitions** — conditional transitions based on index metrics (age, size, doc_count)
- **Notifications** — SNS, Slack, or webhook alerts when policy actions fail or complete

ISM policies are attached to indices via index templates, just like ILM. The ISM background process runs every 30-48 minutes by default and transitions indices through their states.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  opensearch:
    image: opensearchproject/opensearch:2.17.0
    container_name: opensearch
    environment:
      - discovery.type=single-node
      - plugins.security.disabled=true
      - OPENSEARCH_JAVA_OPTS=-Xms1g -Xmx1g
    ports:
      - "9200:9200"
    volumes:
      - os-data:/usr/share/opensearch/data

  opensearch-dashboards:
    image: opensearchproject/opensearch-dashboards:2.17.0
    container_name: opensearch-dashboards
    environment:
      - OPENSEARCH_HOSTS=http://opensearch:9200
    ports:
      - "5601:5601"
    depends_on:
      - opensearch

volumes:
  os-data:
```

### ISM Policy Configuration

```json
PUT _plugins/_ism/policies/logs-policy
{
  "policy": {
    "policy_id": "logs-policy",
    "description": "Log retention policy with notifications",
    "default_state": "hot",
    "states": [
      {
        "name": "hot",
        "actions": [
          {
            "rollover": {
              "min_size": "50gb",
              "min_index_age": "7d"
            }
          }
        ],
        "transitions": [
          {
            "state_name": "warm",
            "conditions": {
              "min_index_age": "7d"
            }
          }
        ]
      },
      {
        "name": "warm",
        "actions": [
          {
            "replica_count": {
              "number_of_replicas": 0
            }
          },
          {
            "force_merge": {
              "max_num_segments": 1
            }
          }
        ],
        "transitions": [
          {
            "state_name": "delete",
            "conditions": {
              "min_index_age": "90d"
            }
          }
        ]
      },
      {
        "name": "delete",
        "actions": [
          {
            "delete": {}
          }
        ]
      }
    ],
    "ism_template": [
      {
        "index_patterns": ["logs-*"],
        "priority": 100
      }
    ]
  }
}
```

### Strengths

- State-based transitions with conditional logic
- Built-in notifications for policy failures
- ISM templates for automatic policy attachment
- Open source under Apache 2.0 license
- Compatible with Elasticsearch ILM policy syntax for migration

### Limitations

- Fewer storage-tier options compared to Elasticsearch (no searchable snapshots out of the box)
- ISM background process runs less frequently than ILM by default
- Dashboards UI for ISM is less polished than Kibana's ILM interface
- Snapshot-based cold storage requires manual configuration

## Comparison: Log Retention Systems

| Feature | Elasticsearch ILM | Loki Retention | OpenSearch ISM |
|---------|-------------------|----------------|----------------|
| Lifecycle model | Multi-phase (hot/warm/cold/delete) | Single retention period | State machine with transitions |
| Rollover support | Yes (size + age triggers) | Automatic chunk management | Yes (size + age triggers) |
| Tiered storage | Hot/warm/cold/frozen tiers | Object storage native | Hot/warm/delete states |
| Compression | Built-in (LZ4, DEFLATE) | Snappy compression | Built-in (LZ4, DEFLATE) |
| Search capability | Full-text with inverted index | Label-based + log content | Full-text with inverted index |
| Multi-tenant | Index-level isolation | Native per-tenant retention | Index-level isolation |
| Notifications | Watcher integration | None built-in | SNS/Slack/webhook native |
| License | SSPL (Server Side Public License) | AGPL v3 | Apache 2.0 |
| Docker image size | ~1.2 GB | ~150 MB | ~1.1 GB |
| Storage efficiency | Medium (full indexing) | High (label-only indexing) | Medium (full indexing) |
| Query performance | Excellent for full-text | Good for label-filtered logs | Excellent for full-text |

## When to Choose Each System

**Choose Elasticsearch ILM** if you need the most feature-rich retention system with searchable snapshots, data tier architecture, and deep Kibana integration. It is ideal for organizations with complex compliance requirements that need to move data through multiple storage tiers while keeping older logs searchable.

**Choose Loki** if your primary concern is storage cost and simplicity. Loki's object storage-native architecture makes it the cheapest option for high-volume log ingestion. The tradeoff is slower full-text search and less granular retention control. For teams already using Prometheus and Grafana, Loki integrates seamlessly.

**Choose OpenSearch ISM** if you need an open-source alternative to Elasticsearch with similar lifecycle management capabilities. ISM's notification system and conditional transitions make it easier to automate policy management. The Apache 2.0 license is also important for organizations with strict open-source requirements.

## Why Self-Host Log Retention?

Self-hosting your log retention infrastructure gives you complete control over data lifecycle policies, compliance boundaries, and storage costs. Cloud-hosted log management services charge per GB ingested and per GB stored, which can become prohibitively expensive at scale. By running Elasticsearch, Loki, or OpenSearch on your own infrastructure, you pay only for the underlying storage and compute.

For organizations in regulated industries, self-hosted retention ensures that log data never leaves your infrastructure. You can implement custom retention policies that align with GDPR, HIPAA, or SOC 2 requirements without relying on third-party data processing agreements.

For related reading, see our [complete log management comparison](../self-hosted-log-management-loki-graylog-opensearch/) and our [log shipping architecture guide](../self-hosted-log-shipping-vector-fluentbit-logstash-guide/). Understanding how logs flow into your storage backend is just as important as managing their lifecycle once stored.

## FAQ

### What is the difference between Elasticsearch ILM and OpenSearch ISM?

Both systems manage index lifecycles through phases/states with actions like rollover, force merge, and delete. The key differences are that OpenSearch ISM adds built-in notifications (SNS, Slack, webhooks) and more flexible conditional transitions between states. Elasticsearch ILM has more advanced storage tier options including searchable snapshots that move data to object storage while keeping it queryable. ISM is Apache 2.0 licensed while ILM is under the SSPL.

### How does Loki handle log deletion?

Loki deletes expired logs through its compactor component. When retention is enabled (`compactor.retention_enabled: true`), the compactor marks chunks that exceed the retention period for deletion during its compaction cycle. Deletion is eventually consistent — it may take several compaction cycles (typically 10-minute intervals) before expired data is fully removed from storage. You must run Loki with the compactor role enabled for retention to work.

### Can I use different retention periods for different log types in Elasticsearch?

Yes. You can create multiple ILM policies and attach them to different index templates. For example, application logs might have a 30-day retention, security audit logs might have a 365-day retention, and debug logs might have a 7-day retention. Each index template references its ILM policy, and the policy is automatically applied when matching indices are created.

### What happens if the ILM/ISM background process fails?

If the lifecycle management process fails, indices will remain in their current state and will not transition to the next phase. This means indices will not be rolled over, shrunk, or deleted automatically. You should monitor the ILM/ISM status via the REST API (`GET _ilm/status` or `GET _plugins/_ism/explain`) and set up alerts for policy failures. OpenSearch ISM's notification feature can automatically alert you when a policy action fails.

### How much storage can I save with proper log retention?

A well-configured retention policy typically reduces storage costs by 60-80% compared to keeping all logs indefinitely. The savings come from: (1) automatically deleting old logs that are no longer needed, (2) moving less-accessed data to cheaper storage tiers, and (3) forcemerging read-only indices to reduce segment overhead. For a system ingesting 100GB/day, a 30-day retention with warm tier optimization typically uses 1-2TB instead of 3TB+.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Log Retention & Lifecycle Management: Elasticsearch ILM vs Loki Retention vs OpenSearch ISM",
  "description": "Compare Elasticsearch ILM, Grafana Loki retention, and OpenSearch ISM for self-hosted log lifecycle management with Docker Compose deployment configs.",
  "datePublished": "2026-05-06",
  "dateModified": "2026-05-06",
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
