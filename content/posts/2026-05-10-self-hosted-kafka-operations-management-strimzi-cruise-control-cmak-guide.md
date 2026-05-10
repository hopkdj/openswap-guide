---
title: "Self-Hosted Kafka Operations Management: Strimzi vs Cruise Control vs CMAK"
date: "2026-05-10"
tags: ["kafka", "event-streaming", "kubernetes", "operators", "devops"]
draft: false
---

Apache Kafka has become the de facto standard for event streaming in modern distributed systems. But running Kafka in production — especially at scale — introduces significant operational complexity: managing brokers, rebalancing partitions, monitoring cluster health, and handling failures. This guide compares three open-source tools that tackle Kafka operations from different angles: **Strimzi** (Kubernetes-native operator), **Cruise Control** (automated rebalancing and self-healing), and **CMAK** (cluster management UI, formerly Yahoo Kafka Manager).

## Why Manage Kafka Operations?

Running Kafka without proper tooling is like flying blind. Broker failures, uneven partition distribution, topic misconfigurations, and consumer lag spikes are daily realities for Kafka operators. Manual intervention is slow and error-prone. The right operations platform automates cluster lifecycle management, optimizes workload distribution, and provides visibility into what your brokers are doing.

Self-hosting your Kafka management stack means you retain full control over cluster configurations, avoid vendor lock-in from managed Kafka services (Confluent Cloud, MSK, Aiven), and keep sensitive event data within your infrastructure boundary. For regulated industries — finance, healthcare, government — this control is non-negotiable.

Kubernetes has become the dominant deployment platform for Kafka, and the three tools we compare each address the operational challenge differently:

| Feature | Strimzi | Cruise Control | CMAK |
|---------|---------|----------------|------|
| **Type** | Kubernetes Operator | Cluster Automation | Management UI |
| **Primary Role** | Deploy and manage Kafka on K8s | Rebalance and self-heal clusters | Monitor and administer clusters |
| **Kubernetes Native** | Yes (CRDs) | No (runs as a service) | No (web application) |
| **Auto-Rebalancing** | Via Cruise Control integration | Yes (core feature) | No |
| **Topic Management** | Via Kubernetes resources | No (broker-level) | Yes (full CRUD) |
| **Consumer Lag Monitoring** | Via Prometheus/JMX | Via JMX metrics | Yes (built-in) |
| **Broker Management** | Via CRD scaling | Yes (add/remove brokers) | Yes (add/remove brokers) |
| **GitHub Stars** | 5,798 | 3,021 | 11,934 |
| **Last Updated** | May 2026 | Nov 2025 | Aug 2023 |
| **License** | Apache 2.0 | BSD 2-Clause | Apache 2.0 |

## Strimzi: Kubernetes-Native Kafka Operator

Strimzi is the leading open-source Kubernetes operator for Apache Kafka. It transforms Kafka from a standalone service into a Kubernetes-native workload managed through Custom Resource Definitions (CRDs).

### Key Features

- **Declarative Kafka management**: Define Kafka clusters, topics, and users as Kubernetes YAML manifests
- **Automated TLS certificate management**: Built-in certificate rotation and mTLS support
- **Kafka Connect and Kafka MirrorMaker**: Managed pipeline components with the same declarative approach
- **Prometheus integration**: Native JMX exporter configuration for monitoring
- **KRaft support**: Native support for Kafka ZooKeeper-free mode
- **Multi-cluster management**: Manage multiple Kafka clusters across namespaces

### Kubernetes Deployment

```bash
# Add the Strimzi Helm repository
helm repo add strimzi https://strimzi.io/charts/
helm repo update

# Install the Strimzi operator
helm install strimzi-kafka-operator strimzi/strimzi-kafka-operator \
  --namespace kafka --create-namespace
```

Deploy a Kafka cluster using a Custom Resource:

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: my-cluster
  namespace: kafka
spec:
  kafka:
    version: 3.7.0
    replicas: 3
    listeners:
      - name: plain
        port: 9092
        type: internal
        tls: false
      - name: tls
        port: 9093
        type: internal
        tls: true
    config:
      offsets.topic.replication.factor: 3
      transaction.state.log.replication.factor: 3
      default.replication.factor: 3
    storage:
      type: jbod
      volumes:
        - id: 0
          type: persistent-claim
          size: 100Gi
          deleteClaim: false
  zookeeper:
    replicas: 3
    storage:
      type: persistent-claim
      size: 50Gi
  entityOperator:
    topicOperator: {}
    userOperator: {}
```

### Docker Compose for Local Testing

For local development without Kubernetes:

```yaml
version: '3.8'
services:
  zookeeper:
    image: quay.io/strimzi/kafka:0.40.0-kafka-3.6.0
    command:
      - sh
      - -c
      - bin/zookeeper-server-start.sh config/zookeeper.properties
    ports:
      - "2181:2181"
    environment:
      LOG_DIR: /tmp/logs

  kafka:
    image: quay.io/strimzi/kafka:0.40.0-kafka-3.6.0
    command:
      - sh
      - -c
      - bin/kafka-server-start.sh config/server.properties
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      LOG_DIR: /tmp/logs
    depends_on:
      - zookeeper
```

## Cruise Control: Automated Kafka Rebalancing

Developed by LinkedIn, Cruise Control is the first tool to fully automate dynamic workload rebalancing and self-healing for Kafka clusters. It monitors broker-level metrics, detects imbalances, and executes partition reassignments without manual intervention.

### Key Features

- **Automatic partition rebalancing**: Distributes partitions evenly across brokers based on configurable goals
- **Self-healing**: Detects broker failures and automatically migrates affected partitions
- **Anomaly detection**: Identifies unusual patterns in broker metrics and triggers corrective actions
- **Capacity planning**: Simulates cluster changes before applying them
- **Configurable optimization goals**: Disk, CPU, network, replica count, and custom goals
- **REST API**: Full programmatic control over cluster operations

### Docker Compose Deployment

Cruise Control deploys alongside an existing Kafka cluster:

```yaml
version: '3.8'
services:
  kafka-1:
    image: confluentinc/cp-kafka:7.6.0
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka-1:9092
      KAFKA_METRIC_REPORTERS: com.linkedin.kafka.cruisecontrol.metricsreporter.CruiseControlMetricsReporter
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: "1"

  cruise-control:
    image: linkedin/cruise-control:2.5.123
    ports:
      - "9090:9090"
    environment:
      CRUISE_CONTROL_ZOOKEEPER_CONNECT: zookeeper:2181
      CRUISE_CONTROL_KAFKA_BROKERLIST: kafka-1:9092
      CRUISE_CONTROL_WEBSERVER_SECURITY_ENABLE: "false"
    depends_on:
      - kafka-1

  zookeeper:
    image: confluentinc/cp-zookeeper:7.6.0
    ports:
      - "2181:2181"
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
```

### Using the Cruise Control REST API

```bash
# Get cluster state
curl http://localhost:9090/kafkacruisecontrol/state

# Trigger a rebalance (dry run first)
curl -X POST "http://localhost:9090/kafkacruisecontrol/rebalance?dryrun=true"

# Execute the rebalance
curl -X POST "http://localhost:9090/kafkacruisecontrol/rebalance?dryrun=false"

# Get cluster model (broker load distribution)
curl "http://localhost:9090/kafkacruisecontrol/kafka_cluster_state"
```

## CMAK: Kafka Cluster Management UI

CMAK (Cluster Manager for Apache Kafka), formerly known as Yahoo Kafka Manager, provides a web-based interface for managing and monitoring Kafka clusters. It is the most widely deployed Kafka management UI with over 11,000 GitHub stars.

### Key Features

- **Multi-cluster management**: Manage multiple Kafka clusters from a single dashboard
- **Topic CRUD operations**: Create, modify, and delete topics through the UI
- **Consumer group monitoring**: View consumer lag, partition assignments, and offset details
- **Broker metrics**: Real-time broker health, throughput, and partition count
- **Preferred replica election**: Trigger elections to restore optimal partition leadership
- **Reassign partitions**: Visual partition reassignment tool
- **JMX metric collection**: Built-in JMX polling for detailed broker metrics

### Docker Compose Deployment

```yaml
version: '3.8'
services:
  cmak:
    image: hlebalbau/kafka-manager:stable
    ports:
      - "9000:9000"
    environment:
      ZK_HOSTS: "zookeeper:2181"
      APPLICATION_SECRET: "random-secret"
      KAFKA_MANAGER_AUTH_ENABLED: "true"
      KAFKA_MANAGER_USERNAME: "admin"
      KAFKA_MANAGER_PASSWORD: "admin123"
    depends_on:
      - zookeeper

  zookeeper:
    image: confluentinc/cp-zookeeper:7.6.0
    ports:
      - "2181:2181"
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
```

### Configuration via UI

After starting CMAK, navigate to `http://localhost:9000` and add your cluster:

1. Click **Cluster** then **Add Cluster**
2. Enter your ZooKeeper connection string (e.g., `zookeeper:2181`)
3. Select your Kafka version
4. Enable JMX polling for detailed metrics
5. Configure consumer offset monitoring (Zookeeper or Kafka-based)
6. Save and the dashboard will populate with broker and topic data

## Choosing the Right Kafka Operations Tool

The three tools serve complementary purposes rather than competing directly:

**Use Strimzi when:**
- Your infrastructure is Kubernetes-native
- You want declarative, GitOps-managed Kafka deployments
- You need automated TLS certificate management and mTLS
- You run Kafka Connect, MirrorMaker, or Kafka Bridge alongside brokers

**Use Cruise Control when:**
- You need automated partition rebalancing across brokers
- Self-healing from broker failures is a requirement
- You operate large clusters (10+ brokers) where manual rebalancing is impractical
- You want capacity planning and what-if analysis capabilities

**Use CMAK when:**
- You need a web UI for day-to-day Kafka administration
- Your team prefers visual topic and consumer management over CLI tools
- You manage multiple Kafka clusters and need a single-pane view
- You need quick access to consumer lag and broker health metrics

**Best practice for production:** Combine Strimzi (for cluster lifecycle) with Cruise Control (for automated rebalancing, which Strimzi can integrate) and CMAK (for operational visibility). Many organizations run all three simultaneously, each handling a different layer of the operations stack.

For event streaming architecture decisions, see our [EventStoreDB vs Kafka vs Pulsar comparison](../2026-04-20-eventstoredb-vs-kafka-vs-pulsar-self-hosted-event-sourcing-guide-2026/) and our [Kafka UI management tools guide](../2026-04-21-kafdrop-vs-akhq-vs-redpanda-console-kafka-ui-management-guide-2026/). For broader CQRS platform comparisons, check our [Axon Server vs EventStoreDB vs Kafka guide](../2026-05-03-axon-server-vs-eventstoredb-vs-kafka-self-hosted-cqrs-platforms-guide/).

## FAQ

### What is the difference between Strimzi and Cruise Control?

Strimzi is a Kubernetes operator that handles the deployment and lifecycle management of Kafka clusters on Kubernetes. Cruise Control is an automation tool that focuses on partition rebalancing and self-healing for existing Kafka clusters. Strimzi answers "how do I run Kafka on K8s?" while Cruise Control answers "how do I keep my Kafka cluster balanced and healthy?"

### Can I use Cruise Control with Strimzi?

Yes. Strimzi supports integrating Cruise Control as an optional component. When you set `cruiseControl: {}` in your Strimzi Kafka CRD, the operator deploys and configures Cruise Control alongside your Kafka cluster, automatically wiring up the metrics reporter.

### Is CMAK still actively maintained?

CMAK last significant update was in August 2023. While the project is not as actively developed as Strimzi or Cruise Control, it remains stable and functional for Kafka versions up to 3.x. For actively developed alternatives, consider Akhq or Redpanda Console for Kafka UI management.

### Does Cruise Control support KRaft (Kafka without ZooKeeper)?

As of the latest release, Cruise Control has experimental KRaft support. However, full production readiness for KRaft mode requires careful testing with your specific Kafka version. Strimzi has native KRaft support and is the recommended path for ZooKeeper-free Kafka deployments.

### How does CMAK collect metrics?

CMAK collects metrics through JMX (Java Management Extensions) polling. It connects to each broker JMX port and retrieves metrics about throughput, partition count, consumer lag, and broker health. You must enable JMX on your Kafka brokers for CMAK to display detailed metrics.

### Which tool should I start with for a small Kafka cluster?

For a small cluster (1-3 brokers), start with CMAK for visibility and basic management. As your cluster grows beyond 5 brokers, add Cruise Control for automated rebalancing. If you are deploying on Kubernetes from the beginning, Strimzi should be your foundation, with Cruise Control as an add-on for large clusters.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Kafka Operations Management: Strimzi vs Cruise Control vs CMAK",
  "description": "Compare Strimzi, Cruise Control, and CMAK for self-hosted Apache Kafka operations management on Kubernetes. Learn about automated rebalancing, cluster lifecycle management, and Kafka monitoring tools.",
  "datePublished": "2026-05-10",
  "dateModified": "2026-05-10",
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
