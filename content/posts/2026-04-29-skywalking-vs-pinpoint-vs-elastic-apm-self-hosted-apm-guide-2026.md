---
title: "SkyWalking vs Pinpoint vs Elastic APM: Best Self-Hosted APM Platform 2026"
date: 2026-04-29
tags: ["comparison", "guide", "self-hosted", "monitoring"]
draft: false
description: "Compare Apache SkyWalking, Pinpoint, and Elastic APM — three powerful open-source application performance monitoring platforms you can self-host. Full Docker deployment guides and feature comparison."
---

When your application runs across dozens of microservices, a slow endpoint is no longer a simple "check the logs" problem. Requests fan out across multiple services, databases, caches, and message queues — and when something goes wrong, you need to see the entire picture. That is exactly what Application Performance Monitoring (APM) tools are built for.

Commercial SaaS APM platforms like Datadog, New Relic, and Dynatrace charge per host, per gigabyte of telemetry, or per million spans. At scale, these costs spiral fast. If you want full control over your telemetry data, unlimited retention, and zero per-seat licensing fees, self-hosted APM is the answer.

This guide compares the three most capable open-source APM platforms you can run on your own infrastructure in 2026: **Apache SkyWalking** (24,792 GitHub stars), **Pinpoint** (13,822 stars), and **Elastic APM** (part of the Elastic Stack). We will cover architecture, instrumentation, storage backends, Docker deployment, and help you pick the right one for your stack.

## Why Self-Host Your APM Platform

The case for running APM on your own servers is stronger than ever:

**Unlimited data retention.** SaaS APM providers delete or downsample your traces after 7-30 days on standard plans. When you self-host, you decide how long to keep trace data — weeks, months, or years. This matters for compliance audits, SLA disputes, and historical performance analysis.

**No telemetry egress costs.** Every span, metric, and error log you send to a cloud ASA provider costs money. At high traffic volumes, ingestion fees alone can exceed your compute bill. Self-hosted APM eliminates this entirely.

**Full data sovereignty.** Telemetry data reveals your architecture, traffic patterns, peak loads, and failure modes. For regulated industries (finance, healthcare, government), sending this data to a third-party platform creates compliance risk. Self-hosting keeps everything inside your perimeter.

**Deep customization.** You can modify retention policies, add custom collectors, integrate with internal alerting systems, and tune sampling rates without asking a vendor for a feature request.

**Cost predictability.** Once your APM infrastructure is running, the marginal cost of ingesting more traces is essentially zero — just disk space and compute. No surprise bills when traffic spikes.

## Apache SkyWalking: Cloud-Native APM for Distributed Systems

[Apache SkyWalking](https://skywalking.apache.org/) is a top-level Apache Software Foundation project designed specifically for cloud-native, microservice-based architectures. It supports automatic instrumentation for Java, .NET, Node.js, Go, Python, PHP, and more through language-specific agents.

### Key Features

- **200+ plugins** for automatic instrumentation across frameworks (Spring Boot, Dubbo, gRPC, Kafka, Redis, MySQL, Elasticsearch, and many more)
- **eBPF-based network profiling** — capture service topology and latency without modifying application code
- **Multiple storage backends** — Elasticsearch, PostgreSQL, MySQL, TiDB, BanyanDB (native), and H2
- **Topology map** — real-time auto-generated service dependency graph with latency heatmap
- **Alarm rules engine** — configurable alerting based on response time, error rate, throughput, and slow queries
- **GraphQL query API** — powerful UI backend for building custom dashboards
- **Continuous profiling** — integrates with Pyroscope/Parca for CPU/Memory flame graphs

### Docker Deployment

SkyWalking provides an official Docker Compose setup. Here is a production-oriented configuration using Elasticsearch as the storage backend:

```yaml
# docker-compose.yml for Apache SkyWalking
version: "3.8"

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    container_name: skywalking-es
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data

  oap:
    image: apache/skywalking-oap-server:10.1.0
    container_name: skywalking-oap
    depends_on:
      elasticsearch:
        condition: service_started
    environment:
      SW_STORAGE: elasticsearch
      SW_STORAGE_ES_CLUSTER_NODES: elasticsearch:9200
      JAVA_OPTS: "-Xms2g -Xmx2g"
    ports:
      - "11800:11800"   # gRPC collector
      - "12800:12800"   # HTTP/GraphQL
    restart: unless-stopped

  ui:
    image: apache/skywalking-ui:10.1.0
    container_name: skywalking-ui
    depends_on:
      - oap
    environment:
      SW_OAP_ADDRESS: http://oap:12800
    ports:
      - "8080:8080"
    restart: unless-stopped

volumes:
  es_data:
```

To instrument a Java application, add the SkyWalking Java agent as a JVM argument:

```bash
java -javaagent:/path/to/skywalking-agent.jar \
     -Dskywalking.agent.service_name=my-service \
     -Dskywalking.collector.backend_service=oap:11800 \
     -jar my-application.jar
```

The agent automatically detects frameworks like Spring Boot, records HTTP requests, database queries, and Redis calls, and sends trace data to the OAP (Observability Analysis Platform) backend via gRPC.

## Pinpoint: Full-Stack APM for Java and PHP Applications

[Pinpoint](https://github.com/pinpoint-apm/pinpoint) was originally developed by Naver (the company behind Naver Search and LINE) to monitor their massive distributed system. It is one of the most mature open-source APM projects, with a focus on **zero-code-change instrumentation** for Java applications.

### Key Features

- **Zero-code-change Java agent** — attach the agent to any JVM application without modifying source code or configuration
- **Distributed transaction tracing** — follow a single request across microservices with full call tree visualization
- **Application topology** — auto-generated service map showing call relationships and latency
- **Real-time active thread monitoring** — see which threads are processing requests, blocked, or idle
- **Support for 20+ Java frameworks** — Spring Boot, Spring Cloud, Apache HttpClient, OkHttp, gRPC, JDBC, Redis (Jedis, Lettuce), Kafka, ActiveMQ, and more
- **PHP agent** — separate agent for PHP applications
- **HBase or Pinot storage** — optimized for high-throughput trace ingestion

### Docker Deployment

Pinpoint uses a separate Docker Compose repository (`pinpoint-apm/pinpoint-docker`). The setup is more complex because it runs multiple components:

```yaml
# docker-compose.yml for Pinpoint (simplified)
# Full version: https://github.com/pinpoint-apm/pinpoint-docker
version: "3.8"

services:
  pinpoint-hbase:
    image: pinpointdocker/pinpoint-hbase:3.0.2
    container_name: pinpoint-hbase
    ports:
      - "60000:60000"
      - "16010:16010"
      - "60020:60020"
      - "16030:16030"
    volumes:
      - hbase_data:/home/pinpoint/hbase
    networks:
      - pinpoint

  pinpoint-mysql:
    image: mysql:8.0
    container_name: pinpoint-mysql
    environment:
      MYSQL_ROOT_PASSWORD: pinpoint
      MYSQL_DATABASE: pinpoint
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    networks:
      - pinpoint

  pinpoint-collector:
    image: pinpointdocker/pinpoint-collector:3.0.2
    container_name: pinpoint-collector
    ports:
      - "9991:9991/tcp"
      - "9992:9992/tcp"
      - "9993:9993/tcp"
      - "9994:9994/udp"
      - "9995:9995/udp"
      - "9996:9996/udp"
    environment:
      CLUSTER_ENABLE: "true"
      CLUSTER_ZOOKEEPER: pinpoint-zookeeper:2181
    depends_on:
      - pinpoint-hbase
      - pinpoint-mysql
    networks:
      - pinpoint

  pinpoint-web:
    image: pinpointdocker/pinpoint-web:3.0.2
    container_name: pinpoint-web
    ports:
      - "8080:8080"
    environment:
      CLUSTER_ENABLE: "true"
      CLUSTER_ZOOKEEPER: pinpoint-zookeeper:2181
    depends_on:
      - pinpoint-collector
    networks:
      - pinpoint

  pinpoint-agent:
    image: pinpointdocker/pinpoint-agent:3.0.2
    container_name: pinpoint-agent
    environment:
      COLLECTOR_IP: pinpoint-collector
      PROFILER_SAMPLING_RATE: "1"
    depends_on:
      - pinpoint-collector
      - pinpoint-web
    networks:
      - pinpoint

networks:
  pinpoint:
    driver: bridge

volumes:
  hbase_data:
  mysql_data:
```

To attach the Pinpoint agent to a Java application:

```bash
java -javaagent:/path/to/pinpoint-bootstrap.jar \
     -Dpinpoint.agentId=my-service-01 \
     -Dpinpoint.applicationName=my-service \
     -jar my-application.jar
```

The agent intercepts method calls at the bytecode level using Java instrumentation APIs, so no code changes are needed.

## Elastic APM: Integrated Observability Within the Elastic Stack

[Elastic APM](https://www.elastic.co/observability/apm) is part of the broader Elastic Stack (Elasticsearch, Logstash, Kibana). If you already run Elasticsearch for search or log management, adding APM is a natural extension — all your telemetry lives in the same cluster.

### Key Features

- **Native Elastic Stack integration** — APM data appears alongside logs, metrics, and uptime checks in Kibana
- **Elastic Agent + Fleet management** — centralized deployment and configuration of APM agents across hundreds of hosts
- **Wide language support** — Java, Python, Node.js, Go, Ruby, PHP, .NET, and RUM (Real User Monitoring) for browser JavaScript
- **Correlated logs and traces** — automatic trace ID injection into log lines so you can jump from a slow trace to the relevant logs
- **Service maps** — auto-generated topology showing service dependencies, error rates, and latency percentiles
- **Custom metrics** — instrument business metrics alongside APM telemetry
- **Synthetic monitoring** — combine APM with active health checks and browser tests

### Docker Deployment

Elastic APM requires Elasticsearch and Kibana. Here is a minimal Docker Compose setup:

```yaml
# docker-compose.yml for Elastic APM
version: "3.8"

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    container_name: apm-elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data

  kibana:
    image: docker.elastic.co/kibana/kibana:8.12.0
    container_name: apm-kibana
    environment:
      ELASTICSEARCH_HOSTS: http://elasticsearch:9200
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

  apm-server:
    image: docker.elastic.co/apm/apm-server:8.12.0
    container_name: apm-server
    environment:
      - apm-server.host=0.0.0.0:8200
      - output.elasticsearch.hosts=["elasticsearch:9200"]
    ports:
      - "8200:8200"
    depends_on:
      - elasticsearch
    command: >
      apm-server -e
        -E apm-server.host=0.0.0.0:8200
        -E output.elasticsearch.hosts=["http://elasticsearch:9200"]
        -E apm-server.auth.anonymous.enabled=true

volumes:
  es_data:
```

To instrument a Python application using the Elastic APM Python agent:

```bash
pip install elastic-apm

# Then either use the middleware for web frameworks:
# Django:
#   Add 'elasticapm.contrib.django' to INSTALLED_APPS
#   Configure ELASTIC_APM in settings.py

# Or use the standalone agent:
export ELASTIC_APM_SERVICE_NAME=my-service
export ELASTIC_APM_SERVER_URL=http://apm-server:8200
export ELASTIC_APM_SECRET_TOKEN=""
```

For Node.js applications, use the `elastic-apm-node` package:

```javascript
const apm = require('elastic-apm-node').start({
  serviceName: 'my-node-service',
  serverUrl: 'http://apm-server:8200',
});
```

## Feature Comparison

| Feature | Apache SkyWalking | Pinpoint | Elastic APM |
|---------|-------------------|----------|-------------|
| **GitHub Stars** | 24,792 | 13,822 | 1,273 (apm-server) |
| **License** | Apache 2.0 | Apache 2.0 | SSPL / Elastic License |
| **Primary Language** | Java | Java | Go |
| **Supported Languages** | Java, .NET, Go, Python, PHP, Node.js, Rust, Lua, C++ | Java, PHP | Java, Python, Go, Node.js, Ruby, PHP, .NET, JS (RUM) |
| **Instrumentation** | Agent-based (bytecode), eBPF, OpenTelemetry, Istio | Agent-based (bytecode, zero-code-change) | Agent-based (SDK), OpenTelemetry, Elastic Agent |
| **Storage Backend** | Elasticsearch, PostgreSQL, MySQL, TiDB, BanyanDB, H2 | HBase, Pinot | Elasticsearch (built-in) |
| **UI/Dashboard** | Built-in web UI | Built-in web UI | Kibana (Observability app) |
| **Service Topology** | Yes (auto-generated) | Yes (auto-generated) | Yes (service maps) |
| **Log Correlation** | Yes | Partial | Yes (native, trace ID injection) |
| **Alerting** | Built-in alarm rules | Limited | Kibana alerting rules |
| **Docker Compose** | Yes (official) | Yes (separate repo) | Yes (official) |
| **OpenTelemetry Support** | Native (OTLP receiver) | Limited | Native (OTLP receiver) |
| **Continuous Profiling** | Yes (Pyroscope/Parca integration) | No | Via Elastic Profiling |
| **Real User Monitoring** | No | No | Yes (browser RUM agent) |
| **Synthetic Monitoring** | No | No | Yes (Heartbeat integration) |
| **Commercial Licensing** | Fully open source | Fully open source | SSPL for full stack features |

## Storage Architecture Comparison

The storage backend is one of the biggest differentiators between these three platforms:

**SkyWalking** gives you the most flexibility. You can choose Elasticsearch for production-scale deployments, PostgreSQL or MySQL for smaller setups, or BanyanDB (a purpose-built time-series database from the SkyWalking team) for optimal performance. The BanyanDB backend eliminates the need for an external database entirely.

**Pinpoint** uses HBase as its primary storage, which is designed for high-throughput write workloads — exactly what trace ingestion produces. This means you need to run HBase (and ZooKeeper) alongside Pinpoint, adding operational complexity. The newer Pinot storage option is faster for time-range queries but still requires managing a distributed data store.

**Elastic APM** stores everything in Elasticsearch, which simplifies the architecture but ties you to the Elastic Stack. If you already run Elasticsearch, this is a net positive — one cluster for logs, metrics, traces, and APM data. If you do not, you need to provision and maintain an Elasticsearch cluster.

## Which Should You Choose?

**Choose Apache SkyWalking if:**
- You need multi-language support (Java, Go, Python, .NET, PHP, Node.js)
- You want the most storage backend options
- You value cloud-native features like eBPF profiling and OpenTelemetry native support
- You prefer a fully open-source project under the Apache Foundation
- You need a built-in web UI without additional dependencies

**Choose Pinpoint if:**
- Your stack is primarily Java-based
- You want truly zero-code-change instrumentation (just attach the agent JAR)
- You need deep JVM-level visibility (active thread monitoring, GC tracing)
- You have existing HBase infrastructure or can manage it
- You want the most mature Java APM agent with the widest framework coverage

**Choose Elastic APM if:**
- You already run the Elastic Stack (Elasticsearch + Kibana)
- You want correlated logs, metrics, and traces in a single interface
- You need Real User Monitoring (browser performance tracking)
- You want centralized agent management via Elastic Agent and Fleet
- Your team is already familiar with Kibana dashboards and query syntax

For related reading, see our [SigNoz vs Jaeger vs Uptrace distributed tracing guide](../signoz-jaeger-uptrace-self-hosted-apm-distributed-tracing-guide/) for a comparison of pure tracing platforms, and our [HertzBeat vs Prometheus vs Netdata infrastructure monitoring guide](../2026-04-25-hertzbeat-vs-prometheus-vs-netdata-self-hosted-monitoring-guide/) for complementary infrastructure-level monitoring. If you need continuous profiling alongside APM, check out our [Grafana Pyroscope vs Parca vs Profefe guide](../2026-04-18-grafana-pyroscope-vs-parca-vs-profefe-self-hosted-continuous-profiling-guide-2026/).

## FAQ

### What is the difference between APM and distributed tracing?

APM (Application Performance Monitoring) is a broader category that includes distributed tracing, but also covers metrics, error tracking, service topology, and alerting. Distributed tracing focuses specifically on following individual requests as they traverse multiple services. Tools like Jaeger specialize in tracing, while SkyWalking and Pinpoint provide full APM — tracing plus metrics, topology maps, dashboards, and alerting.

### Do I need to modify my application code to use these APM tools?

For Java applications, both SkyWalking and Pinpoint support bytecode-level instrumentation via Java agents — you only need to add a `-javaagent` JVM argument, no code changes required. For other languages (Go, Python, Node.js), you typically need to install an SDK or library and add a few lines of initialization code. Elastic APM provides SDKs for each supported language with minimal boilerplate.

### How much storage do I need for self-hosted APM?

Trace data is voluminous. A moderate production system generating 1,000 traces per second at ~5KB per trace produces roughly 432 GB of raw trace data per day. With sampling (e.g., 10% of traces), this drops to ~43 GB/day. SkyWalking and Pinpoint support configurable sampling rates. Elasticsearch (used by SkyWalking and Elastic APM) typically compresses trace data by 3-5x. Plan for 50-200 GB per day depending on traffic and sampling.

### Can I use OpenTelemetry with any of these platforms?

Yes. Apache SkyWalking has native OpenTelemetry support through its OTLP receiver, so you can send OTLP traces directly to the OAP backend. Elastic APM also accepts OTLP data in recent versions. Pinpoint has more limited OTLP support — its strength is in its native Java agent. If OpenTelemetry compatibility is a priority, SkyWalking or Elastic APM are the better choices.

### Is Elastic APM truly free to self-host?

The core APM features are available under the Elastic License (free for self-hosted use). However, some advanced Kibana features (machine learning-based anomaly detection, advanced alerting) require a paid subscription. SkyWalking and Pinpoint are fully open source under Apache 2.0 with no premium tiers.

### Which APM platform has the lowest operational overhead?

SkyWalking has the simplest deployment if you use its built-in H2 or PostgreSQL storage — just the OAP server and UI containers. Elastic APM is simplest if you already run Elasticsearch — you just add the APM server container. Pinpoint has the highest overhead because it requires HBase (or Pinot) plus ZooKeeper, MySQL, collector, and web components — at minimum 5-6 containers.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "SkyWalking vs Pinpoint vs Elastic APM: Best Self-Hosted APM Platform 2026",
  "description": "Compare Apache SkyWalking, Pinpoint, and Elastic APM — three powerful open-source application performance monitoring platforms you can self-host. Full Docker deployment guides and feature comparison.",
  "datePublished": "2026-04-29",
  "dateModified": "2026-04-29",
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
