---
title: "Self-Hosted Redis Operators for Kubernetes: OT Container Kit vs Spotahome vs IBM"
date: "2026-05-10"
tags: ["redis", "kubernetes", "operators", "cache", "database", "devops"]
draft: false
---

Redis is the most popular in-memory data store, used for caching, session management, message brokering, and real-time analytics. Running Redis on Kubernetes introduces unique challenges: managing high-availability clusters with Sentinel, handling failover, provisioning persistent storage, and scaling read replicas. Redis operators automate these operational tasks. This guide compares three open-source Redis operators for Kubernetes: **OT Container Kit Redis Operator** (most actively developed), **Spotahome Redis Operator** (pioneering Sentinel-based HA), and **IBM Redis Cluster Operator** (enterprise-grade cluster management).

## Why Use a Redis Operator on Kubernetes?

Deploying Redis on Kubernetes without an operator means manually managing StatefulSets, Services, ConfigMaps, and failover scripts. When a Redis master pod crashes, Kubernetes restarts it — but it does not promote a replica to master. A Redis operator watches the cluster state and automates:

- **Automatic failover**: Promoting replicas when the master becomes unreachable
- **Cluster provisioning**: Creating multi-node Redis or Redis Cluster deployments from a single manifest
- **Configuration management**: Applying Redis configuration changes without downtime
- **Backup and restore**: Automated RDB and AOF snapshots
- **Scaling**: Adding or removing replicas through simple CRD updates
- **Monitoring**: Exporting Redis metrics to Prometheus

The three operators we compare take different architectural approaches to these challenges:

| Feature | OT Container Kit | Spotahome | IBM Redis Cluster |
|---------|-----------------|-----------|-------------------|
| **Cluster Mode** | Standalone, Cluster, Sentinel, Replication | Sentinel-only | Redis Cluster |
| **Auto-Failover** | Yes (all modes) | Yes (Sentinel) | Yes (Cluster) |
| **Backup/Restore** | Yes (built-in) | No | No |
| **Monitoring** | Prometheus exporter | No | No |
| **Helm Chart** | Yes | Yes | Yes |
| **GitHub Stars** | 1,344 | 1,666 | 60 |
| **Last Updated** | Apr 2026 | Jul 2024 | Sep 2025 |
| **Language** | Go | Go | Go |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |

## OT Container Kit Redis Operator

The OT Container Kit Redis Operator is the most actively developed open-source Redis operator for Kubernetes. It supports four deployment modes — standalone, cluster, replication, and Sentinel — and includes built-in backup, restore, and monitoring capabilities.

### Key Features

- **Four deployment modes**: Standalone (single node), Cluster (distributed hash slots), Replication (master-replica), and Sentinel (HA with automatic failover)
- **Built-in backup and restore**: Automated RDB snapshots with configurable schedules
- **Prometheus metrics**: Integrated redis_exporter sidecar for monitoring
- **TLS support**: Automatic certificate management for encrypted Redis connections
- **Password management**: Kubernetes Secret integration for Redis authentication
- **Resource management**: CPU and memory limits per node with QoS guarantees

### Helm Installation

```bash
# Add the Helm repository
helm repo add ot-helm https://ot-container-kit.github.io/helm-charts/
helm repo update

# Install the operator
helm install redis-operator ot-helm/redis-operator   --namespace redis-operator --create-namespace
```

### Deploy a Sentinel-Based HA Cluster

```yaml
apiVersion: redis.redis.opstreelabs.in/v1beta2
kind: RedisCluster
metadata:
  name: redis-ha
  namespace: redis
spec:
  clusterSize: 3
  clusterVersion: v7
  securityContext:
    runAsUser: 1000
    fsGroup: 1000
  redisExporter:
    enabled: true
    image: oliver006/redis_exporter:v1.58.0
  storage:
    volumeClaimTemplate:
      spec:
        accessModes:
          - ReadWriteOnce
        resources:
          requests:
            storage: 1Gi
        storageClassName: standard
  podSecurityContext:
    runAsUser: 1000
    fsGroup: 1000
  redisConfig:
    additionalRedisConfig: redis-redis-conf
  serviceMonitor:
    enabled: true
```

### Deploy a Redis Cluster (Sharded)

```yaml
apiVersion: redis.redis.opstreelabs.in/v1beta2
kind: RedisCluster
metadata:
  name: redis-cluster
  namespace: redis
spec:
  clusterSize: 3
  clusterVersion: v7
  clusterMode: cluster
  redisExporter:
    enabled: true
  storage:
    volumeClaimTemplate:
      spec:
        accessModes:
          - ReadWriteOnce
        resources:
          requests:
            storage: 5Gi
```

### Docker Compose for Local Testing

While the operator is Kubernetes-native, you can test the underlying Redis Sentinel setup locally:

```yaml
version: '3.8'
services:
  redis-master:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-master-data:/data
    command: redis-server --appendonly yes

  redis-replica:
    image: redis:7-alpine
    ports:
      - "6380:6379"
    command: redis-server --replicaof redis-master 6379 --appendonly yes
    depends_on:
      - redis-master

  redis-sentinel:
    image: redis:7-alpine
    ports:
      - "26379:26379"
    command: >
      redis-sentinel /usr/local/etc/redis/sentinel.conf
    volumes:
      - ./sentinel.conf:/usr/local/etc/redis/sentinel.conf
    depends_on:
      - redis-master

volumes:
  redis-master-data:
```

```bash
# sentinel.conf
sentinel monitor mymaster redis-master 6379 2
sentinel down-after-milliseconds mymaster 5000
sentinel failover-timeout mymaster 60000
sentinel parallel-syncs mymaster 1
```

## Spotahome Redis Operator

Spotahome pioneered the Redis Sentinel operator pattern for Kubernetes. It is simpler and more focused than OT Container Kit, concentrating exclusively on Redis Sentinel-based high availability. While less actively maintained, it remains a solid choice for organizations that need straightforward Sentinel deployments.

### Key Features

- **Sentinel-focused**: Purpose-built for Redis Sentinel HA deployments
- **Simple API**: Minimal CRD surface area — easy to understand and use
- **Automatic failover**: Sentinel-based master promotion on pod failure
- **Configuration reload**: Dynamic Redis configuration updates
- **Battle-tested**: Deployed in production at Spotahome since 2018

### Helm Installation

```bash
# Add the Helm repository
helm repo add spotahome-redis-operator https://spotahome.github.io/redis-operator
helm repo update

# Install the operator
helm install redis-operator spotahome-redis-operator/redis-operator   --namespace redis-operator --create-namespace
```

### Deploy a RedisFailover

```yaml
apiVersion: databases.spotahome.com/v1
kind: RedisFailover
metadata:
  name: redis-ha
  namespace: redis
spec:
  sentinel:
    replicas: 3
    resources:
      requests:
        cpu: 100m
        memory: 100Mi
      limits:
        cpu: 200m
        memory: 200Mi
  redis:
    replicas: 3
    resources:
      requests:
        cpu: 150m
        memory: 400Mi
      limits:
        cpu: 250m
        memory: 500Mi
    storage:
      persistentVolumeClaim:
        metadata:
          name: redis-data
        spec:
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 5Gi
    exporter:
      enabled: true
      image: oliver006/redis_exporter:v1.58.0
    customConfig:
      - maxmemory-policy allkeys-lru
      - appendonly yes
```

## IBM Redis Cluster Operator

IBM Redis Cluster Operator manages Redis Cluster deployments (the native Redis sharding mode) on Kubernetes. It is designed for large-scale, distributed Redis deployments that require horizontal scaling through hash slot partitioning.

### Key Features

- **Redis Cluster mode**: Native support for Redis sharding with 16,384 hash slots
- **Automatic slot rebalancing**: Reassigns hash slots when nodes are added or removed
- **Multi-node coordination**: Manages the gossip protocol and cluster state
- **Enterprise focus**: Designed for IBM Cloud Pak and enterprise Kubernetes environments
- **Helm-based installation**: Standard Kubernetes deployment pattern

### Helm Installation

```bash
# Install via Helm
helm install redis-cluster-operator ibm-charts/redis-cluster-operator   --namespace redis-operator --create-namespace
```

### Deploy a Redis Cluster

```yaml
apiVersion: db.ibm.com/v1alpha1
kind: RedisCluster
metadata:
  name: my-redis-cluster
  namespace: redis
spec:
  replicas: 6
  masterReplicas: 3
  replicaReplicas: 3
  image: redis:7-alpine
  resources:
    requests:
      cpu: 200m
      memory: 512Mi
    limits:
      cpu: 500m
      memory: 1Gi
  storage:
    size: 10Gi
    storageClass: standard
  redisConf:
    maxmemory: 400mb
    maxmemory-policy: allkeys-lru
```

## Choosing the Right Redis Operator

The three operators target different operational requirements:

**Use OT Container Kit when:**
- You need the most feature-rich and actively maintained operator
- You want multiple deployment modes (Standalone, Cluster, Replication, Sentinel)
- Built-in backup, restore, and Prometheus monitoring are requirements
- You need TLS support and password management out of the box

**Use Spotahome when:**
- You only need Redis Sentinel-based high availability
- You prefer a simpler, more focused API surface
- Your organization has existing Spotahome operator experience
- You do not need backup/restore or monitoring features from the operator

**Use IBM Redis Cluster Operator when:**
- You specifically need Redis Cluster mode (sharding across nodes)
- You are deploying in an IBM Cloud Pak or enterprise Kubernetes environment
- You need large-scale horizontal scaling with automatic slot rebalancing
- Your team prefers IBM-supported open-source tooling

For Redis performance tuning, see our [distributed caching alternatives guide](../self-hosted-distributed-caching-redis-alternatives-guide-2026/) and [Redis GUI management tools](../2026-04-23-redis-commander-vs-redis-insight-vs-ardm-self-hosted-redis-gui-2026/). For cache proxy patterns, check our [twemproxy vs mcrouter vs Envoy guide](../2026-04-25-twemproxy-vs-mcrouter-vs-envoy-self-hosted-cache-proxy-guide-2026/).

## FAQ

### What is the difference between Redis Sentinel and Redis Cluster?

Redis Sentinel provides high availability through automatic failover — when the master fails, a replica is promoted. It does not shard data. Redis Cluster provides horizontal scaling by distributing data across multiple nodes using 16,384 hash slots. Sentinel is for HA, Cluster is for scaling. You can use both together for maximum resilience.

### Which operator supports the latest Redis 7 features?

All three operators support Redis 7. OT Container Kit has the most recent updates with explicit Redis 7 configuration options. Spotahome supports Redis 7 but has not been updated since mid-2024. IBM operator supports Redis 7 as of its September 2025 update.

### Can I migrate between operators without data loss?

Yes, but the process depends on your deployment mode. For Sentinel-based deployments, you can run the old and new operator side-by-side, then switch the RedisFailover CRD to the new operator and let it adopt the existing pods. For Cluster mode, you need to export RDB snapshots and import them into the new cluster.

### Does the OT Container Kit operator support Redis on ARM64?

Yes. The OT Container Kit operator and its managed Redis containers support both amd64 and arm64 architectures, making it suitable for deployment on AWS Graviton, Apple Silicon, and Raspberry Pi Kubernetes clusters.

### How does Redis operator handle persistent storage?

Redis operators use Kubernetes PersistentVolumeClaims (PVCs) to store Redis data. When a pod is rescheduled to a different node, Kubernetes attaches the same PVC to the new pod, preserving the data. The storage class determines whether the volume is dynamically provisioned or pre-created.

### Should I use an operator or a Helm chart for Redis?

Helm charts deploy static Redis configurations — they do not manage runtime state. Operators watch the cluster and react to changes (failovers, scaling, configuration updates). For production Redis with high availability requirements, use an operator. For development or simple caching needs, a Helm chart is sufficient.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Redis Operators for Kubernetes: OT Container Kit vs Spotahome vs IBM",
  "description": "Compare OT Container Kit, Spotahome, and IBM Redis operators for Kubernetes. Learn about Redis Sentinel, Cluster mode, automatic failover, and backup strategies.",
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
