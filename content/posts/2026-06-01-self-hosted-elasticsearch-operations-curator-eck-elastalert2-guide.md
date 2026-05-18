---
title: "Self-Hosted Elasticsearch Operations: Curator vs ECK vs ElastAlert 2"
date: "2026-05-18"
tags: ["elasticsearch", "cluster-management", "devops", "log-management"]
draft: false
---

Running Elasticsearch in production requires more than just starting the service. Index lifecycle management, cluster orchestration, automated alerting, and backup strategies are all essential for a reliable search and analytics platform. While Elasticsearch provides powerful built-in capabilities, the open-source ecosystem offers specialized tools that simplify operations at scale.

This guide compares three essential Elasticsearch operations tools: **Elastic Curator** for index lifecycle management, **Elastic Cloud on Kubernetes (ECK)** for cluster orchestration, and **ElastAlert 2** for alerting and anomaly detection.

## Quick Comparison

| Feature | Elastic Curator | ECK (Cloud on K8s) | ElastAlert 2 |
|---------|----------------|-------------------|--------------|
| GitHub Stars | 3,087+ | 2,843+ | 1,118+ |
| Primary Role | Index lifecycle | Cluster orchestration | Alerting engine |
| Deployment | Cron job / Docker | Kubernetes Operator | Docker / pip |
| Index Management | Yes (core focus) | Yes (via ILM) | No |
| Cluster Provisioning | No | Yes (core focus) | No |
| Alerting | No | Basic (via CRD) | Yes (core focus) |
| Backup/Restore | Snapshot helpers | Snapshot CRD | No |
| Kubernetes Native | No | Yes | No |
| Best For | Index rotation, cleanup | K8s cluster management | Rule-based alerting |

## Elastic Curator

Elastic Curator is the original Elasticsearch index management tool, designed to automate the creation, rollover, and deletion of time-based indices. It is particularly valuable for log management workflows where daily or hourly indices accumulate rapidly.

### Key Features

- **Index lifecycle actions** — Create, delete, close, open, snapshot, and restore indices
- **Age-based filtering** — Target indices older or younger than a specified threshold
- **Snapshot management** — Automate backups to S3, GCS, or local repositories
- **Index aliasing** — Manage read/write aliases for seamless index rotation
- **Configuration-driven** — YAML action files define exactly what operations to run
- **CLI and API** — Run as a cron job or integrate into CI/CD pipelines

### Docker Compose Deployment

```yaml
version: "3"
services:
  curator:
    image: elastic/curator:latest
    container_name: elasticsearch-curator
    volumes:
      - ./curator/config:/curator
    environment:
      - ES_HOST=elasticsearch
      - ES_PORT=9200
    command: ["--config", "/curator/curator.yml", "/curator/action_file.yml"]
    depends_on:
      - elasticsearch

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
```

### Sample Action File (Delete Old Indices)

```yaml
actions:
  1:
    action: delete_indices
    description: "Delete indices older than 30 days"
    options:
      ignore_empty_list: true
      timeout_override: 300
      continue_if_exception: true
    filters:
      - filtertype: pattern
        kind: prefix
        value: "logstash-"
      - filtertype: age
        source: name
        direction: older
        timestring: "%Y.%m.%d"
        unit: days
        unit_count: 30
```

### Installation

```bash
pip install elasticsearch-curator

# Run curator with config and action files
curator --config /path/to/curator.yml /path/to/action_file.yml

# Or schedule via cron
0 2 * * * curator --config /etc/curator/curator.yml /etc/curator/daily_actions.yml
```

## Elastic Cloud on Kubernetes (ECK)

ECK is the official Kubernetes operator for Elasticsearch, developed by Elastic. It transforms Elasticsearch from a manually-managed stateful application into a declarative Kubernetes resource, handling cluster provisioning, upgrades, scaling, and day-2 operations automatically.

### Key Features

- **Declarative cluster management** — Define Elasticsearch clusters as Kubernetes Custom Resources
- **Automated upgrades** — Rolling upgrades with zero downtime
- **Autoscaling** — Horizontal and vertical scaling based on resource metrics
- **TLS certificate management** — Automatic certificate rotation for node-to-node encryption
- **Multi-cluster support** — Manage multiple Elasticsearch clusters across namespaces
- **Kibana integration** — Deploy and manage Kibana instances alongside clusters
- **Backup CRD** — Declarative snapshot and restore operations

### Kubernetes Deployment

```yaml
apiVersion: elasticsearch.k8s.elastic.co/v1
kind: Elasticsearch
metadata:
  name: production-cluster
spec:
  version: 8.12.0
  nodeSets:
    - name: master-nodes
      count: 3
      config:
        node.roles: ["master"]
        node.store.allow_mmap: false
      volumeClaimTemplates:
        - metadata:
            name: elasticsearch-data
          spec:
            accessModes: ["ReadWriteOnce"]
            resources:
              requests:
                storage: 100Gi
    - name: data-nodes
      count: 3
      config:
        node.roles: ["data", "ingest"]
        node.store.allow_mmap: false
      volumeClaimTemplates:
        - metadata:
            name: elasticsearch-data
          spec:
            accessModes: ["ReadWriteOnce"]
            resources:
              requests:
                storage: 500Gi
      podTemplate:
        spec:
          containers:
            - name: elasticsearch
              resources:
                requests:
                  memory: 4Gi
                  cpu: 1
                limits:
                  memory: 8Gi
                  cpu: 2
---
apiVersion: kibana.k8s.elastic.co/v1
kind: Kibana
metadata:
  name: production-kibana
spec:
  version: 8.12.0
  count: 1
  elasticsearchRef:
    name: production-cluster
```

### Installation

```bash
# Install ECK operator
kubectl apply -f https://download.elastic.co/downloads/eck/2.11.0/crds.yaml
kubectl apply -f https://download.elastic.co/downloads/eck/2.11.0/operator.yaml

# Create Elasticsearch cluster
kubectl apply -f elasticsearch-cluster.yaml

# Get credentials
kubectl get secret production-cluster-es-elastic-user -o jsonpath='{.data.elastic}' | base64 --decode
```

## ElastAlert 2

ElastAlert 2 is the community-maintained continuation of Yelp's original ElastAlert project. It monitors Elasticsearch for patterns that match predefined rules and triggers alerts through various channels — email, Slack, webhooks, PagerDuty, and more.

### Key Features

- **Rule-based alerting** — Frequency, spike, flatline, whitelist, blacklist, and custom rules
- **Multiple alert channels** — Email, Slack, MS Teams, PagerDuty, Jira, webhooks, Telegram
- **Alert aggregation** — Combine multiple matches into single notifications
- **Silence management** — Prevent alert fatigue with configurable silence periods
- **Alert replay** — Re-trigger alerts if the condition persists after silence expires
- **REST API** — Programmatic rule management via elastalert2-server
- **Template engine** — Customize alert messages with Jinja2 templates

### Docker Compose Deployment

```yaml
version: "3"
services:
  elastalert2:
    image: ghcr.io/jertel/elastalert2/elastalert2:latest
    container_name: elastalert2
    restart: unless-stopped
    volumes:
      - ./elastalert2/config:/opt/elastalert/config
      - ./elastalert2/rules:/opt/elastalert/rules
      - ./elastalert2/logs:/opt/elastalert/logs
    environment:
      - ES_HOST=elasticsearch
      - ES_PORT=9200
      - RUN_ELASTALERT=true
    depends_on:
      - elasticsearch

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
```

### Sample Alert Rule

```yaml
name: "High Error Rate Alert"
type: frequency
index: "logstash-*"
num_events: 50
timeframe:
  minutes: 5
filter:
  - query:
      query_string:
        query: "level:ERROR"
alert:
  - "slack"
slack_webhook_url: "https://hooks.slack.com/services/XXXXX/YYYYY/ZZZZZ"
slack_msg_color: "danger"
alert_text: "High error rate detected: {0} errors in the last 5 minutes."
alert_text_args: ["num_events"]
```

### Installation

```bash
# Install via pip
pip install elastalert2

# Or use Docker
docker run -d --name elastalert2   -v $(pwd)/config:/opt/elastalert/config   -v $(pwd)/rules:/opt/elastalert/rules   ghcr.io/jertel/elastalert2/elastalert2:latest
```

## Choosing the Right Elasticsearch Operations Tool

**Choose Elastic Curator** if you:
- Need automated index rotation and cleanup for log pipelines
- Run Elasticsearch outside Kubernetes (bare metal, VMs, Docker)
- Want fine-grained control over index lifecycle with YAML configuration
- Primarily manage time-series data with predictable rollover patterns

**Choose ECK** if you:
- Run Elasticsearch on Kubernetes and want native operator management
- Need automated cluster provisioning, scaling, and upgrades
- Require TLS certificate management and security automation
- Manage multiple Elasticsearch clusters with declarative configuration

**Choose ElastAlert 2** if you:
- Need proactive alerting on Elasticsearch data patterns
- Want to replace manual log monitoring with automated rule-based alerts
- Require integration with Slack, PagerDuty, or other incident management tools
- Monitor application logs, metrics, or security events in real time

## Why Self-Host Elasticsearch Operations Tools?

Running Elasticsearch without proper operations tooling leads to several predictable problems that compound over time.

**Index sprawl**: Without automated lifecycle management, Elasticsearch clusters accumulate thousands of indices over time. Each index consumes file descriptors, memory, and disk space. Curator prevents this by automatically rolling over, closing, and deleting old indices based on configurable retention policies. For related log management strategies, see our [log retention lifecycle guide](../2026-05-06-self-hosted-log-retention-lifecycle-management-elasticsearch-ilm-loki-opensearch-ism/).

**Cluster reliability**: Manual Elasticsearch cluster management is error-prone. Node failures, version upgrades, and configuration changes require careful coordination. ECK handles all of this automatically — upgrading nodes one at a time, rebalancing shards, and managing TLS certificates without human intervention. If you are also managing [observability dashboards](../2026-05-17-self-hosted-observability-dashboards-opensearch-grafana-kibana-guide/) across multiple monitoring systems, ECK ensures the Elasticsearch backend stays healthy.

**Proactive incident response**: Elasticsearch clusters process millions of events per hour. Without automated alerting, critical issues go unnoticed until they cause outages. ElastAlert 2 monitors your indices for anomaly patterns and notifies the right team before problems escalate. Combined with our [infrastructure monitoring comparison](../2026-04-26-checkmk-vs-zabbix-vs-nagios-self-hosted-infrastructure-monitoring-2026/), you get comprehensive alerting coverage.

## FAQ

### Can I use all three tools together?

Yes, they are complementary. ECK manages the Elasticsearch cluster lifecycle, Curator handles index rotation and cleanup, and ElastAlert 2 provides alerting on indexed data. Many production environments use all three in combination.

### Does ECK replace Curator?

Partially. ECK includes Index Lifecycle Management (ILM) through Elasticsearch's built-in ILM policies, which covers many of Curator's use cases. However, Curator still offers more granular control over snapshot management and complex index operations that ILM does not support.

### Is ElastAlert 2 compatible with OpenSearch?

ElastAlert 2 is designed for Elasticsearch. For OpenSearch, consider using OpenSearch Alerting (built into the OpenSearch Dashboards) or the open-source OpenSearch alerting plugins.

### How does ECK handle data persistence?

ECK uses Kubernetes PersistentVolumeClaims (PVCs) for Elasticsearch data directories. When a node is replaced during an upgrade or rescheduling, the new pod reattaches the same PVC, preserving all data. For production deployments, use storage classes that support dynamic provisioning.

### What alert types does ElastAlert 2 support?

ElastAlert 2 supports frequency (N events in X time), spike (sudden increase/decrease), flatline (no events for X time), whitelist/blacklist matches, cardinality, and custom Python rule types. Each rule type can trigger multiple alert channels simultaneously.

### How do I migrate from Yelp's original ElastAlert to ElastAlert 2?

ElastAlert 2 is a drop-in replacement. Most existing rule configurations work without modification. The main changes are updated Python dependencies, Docker image paths, and a few renamed configuration options. The project maintains a migration guide on GitHub.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Elasticsearch Operations: Curator vs ECK vs ElastAlert 2",
  "description": "Compare Elasticsearch operations tools: Elastic Curator for index management, ECK for Kubernetes orchestration, and ElastAlert 2 for alerting. Docker configs included.",
  "datePublished": "2026-05-18",
  "dateModified": "2026-05-18",
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
