---
title: "Self-Hosted Java APM: Scouter vs Glowroot vs Kamon"
date: "2026-06-04"
tags: ["apm", "java", "monitoring", "performance", "observability", "self-hosted", "devops"]
draft: false
---

## Introduction

When your Java application hits production, understanding what's happening under the hood becomes critical. Application Performance Monitoring (APM) tools give you visibility into request latency, error rates, database queries, and memory usage — all without modifying your application code. While commercial APM solutions like Datadog and New Relic dominate the market, several powerful open-source alternatives exist for teams that want to self-host their monitoring stack.

In this guide, we compare three self-hosted Java APM tools: **Scouter**, **Glowroot**, and **Kamon**. Each takes a fundamentally different approach to application monitoring, from LG CNS's enterprise-grade Scouter to the lightweight Glowroot and the metrics-focused Kamon ecosystem.

## Comparison Table

| Feature | Scouter | Glowroot | Kamon |
|---------|---------|----------|-------|
| **Stars** | 2,174 | 1,337 | 1,429 |
| **Language** | Java | Java | Scala (JVM) |
| **Overhead** | Low | Very low | Low |
| **Architecture** | Agent + Collector + Server | Agent + Embedded UI | Agent SDK + Reporter |
| **Storage Backend** | Custom (Scalable) | Embedded H2 (per JVM) | Prometheus, InfluxDB, Elasticsearch |
| **Dashboard** | Web UI + Real-time | Per-JVM Web UI | Grafana (via Prometheus) |
| **Distributed Tracing** | ✓ (XLog) | ✓ (transaction traces) | ✓ (Zipkin/Jaeger compatible) |
| **Alerting** | ✓ (Plugin-based) | ✗ | Via Alertmanager |
| **SQL Monitoring** | ✓ | ✓ | Via JDBC instrumentation |
| **Docker Support** | ✓ (Official image) | ✓ (Embedded agent) | ✓ (Agent as sidecar) |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |

## Scouter: Enterprise APM by LG CNS

Scouter is an open-source APM developed by LG CNS, designed for monitoring large-scale Java applications. Unlike many APM tools that focus on per-instance monitoring, Scouter uses a **collector-based architecture** that aggregates metrics from multiple application servers into a centralized view.

### Key Features

- **XLog**: Scouter's distributed tracing system captures end-to-end request flows across microservices, similar to commercial APM solutions
- **Real-time Thread Monitoring**: View active threads, CPU usage, and memory consumption per JVM instance — useful for diagnosing production issues in real time
- **Plugin System**: Extend Scouter with custom counters for business metrics, database connection pools, and framework-specific instrumentation
- **Counter Engine**: Time-series metrics with configurable aggregation intervals (5s default) for high-resolution monitoring

### Docker Compose Deployment

Scouter provides official Docker images for all components. Here's a minimal deployment stack:

```yaml
version: '3.8'
services:
  scouter-collector:
    image: scouterapm/scouter-collector:latest
    ports:
      - "6100:6100/tcp"
      - "6100:6100/udp"
    volumes:
      - ./scouter-collector/conf:/scouter/conf
    restart: unless-stopped

  scouter-server:
    image: scouterapm/scouter-server:latest
    ports:
      - "6180:6180"
    environment:
      - SCOUTER_COLLECTOR_IP=scouter-collector
    volumes:
      - scouter-data:/scouter/server/data
    depends_on:
      - scouter-collector
    restart: unless-stopped

volumes:
  scouter-data:
```

To instrument your Java application, add the Scouter agent as a JVM argument:

```bash
java -javaagent:/path/to/scouter/agent.java/scouter.agent.jar \
  -Dscouter.config=/path/to/scouter/agent.java/conf/scouter.conf \
  -Dobj_name=my-application \
  -jar my-app.jar
```

**Best for**: Teams running 10+ JVM instances who need centralized monitoring with distributed tracing and real-time diagnostics.

## Glowroot: Lightweight Per-JVM APM

Glowroot takes a radically different approach — it's a **self-contained APM agent** that embeds its own UI and storage engine directly inside each JVM. There are no external servers, databases, or infrastructure dependencies. Download one JAR, attach it to your application, and access the dashboard at `http://localhost:4000`.

### Key Features

- **Zero Infrastructure**: No external databases, collectors, or servers needed. Glowroot stores data in an embedded H2 database within the JVM process
- **Extremely Low Overhead**: Glowroot uses ASM bytecode instrumentation with careful filtering to minimize CPU and memory impact — typically under 1% overhead
- **Transaction Traces**: Capture full traces of slow requests with SQL query timing, external HTTP calls, and method-level profiling
- **JVM Health Dashboard**: Built-in pages for heap usage, GC activity, thread dumps, and MBean metrics
- **Continuous Profiling**: Lightweight CPU sampling that shows which methods consume the most time

### Deployment (Single-JVM)

Glowroot is deployed as a single JAR with no external dependencies:

```bash
# Download Glowroot
wget https://github.com/glowroot/glowroot/releases/download/v0.14.0/glowroot-0.14.0-dist.zip
unzip glowroot-0.14.0-dist.zip

# Attach to your Java application
java -javaagent:path/to/glowroot/glowroot.jar \
  -jar my-app.jar

# Access dashboard at http://localhost:4000
```

For Docker deployments, mount Glowroot as a volume:

```yaml
version: '3.8'
services:
  java-app:
    image: your-java-app:latest
    environment:
      - JAVA_TOOL_OPTIONS=-javaagent:/glowroot/glowroot.jar
    volumes:
      - ./glowroot:/glowroot
    ports:
      - "4000:4000"
      - "8080:8080"
```

**Best for**: Individual developers and small teams who want APM without infrastructure overhead. Ideal for staging environments, development debugging, and single-instance production monitoring.

## Kamon: Metrics-First Observability

Kamon is a **JVM instrumentation library** that focuses on generating high-quality metrics, traces, and context propagation for your applications. Unlike Scouter and Glowroot — which are primarily monitoring UIs with agents — Kamon is a telemetry pipeline that integrates with existing observability stacks like Prometheus, Grafana, and Zipkin.

### Key Features

- **Automatic Instrumentation**: Instrument popular frameworks (Akka, Play, Spring, Lagom) with zero code changes using Kamon's agent
- **Multi-Backend Reporting**: Export metrics to Prometheus, InfluxDB, Datadog, or StatsD; traces to Zipkin or Jaeger
- **Context Propagation**: Propagate trace context across HTTP, gRPC, and messaging protocols for end-to-end distributed tracing
- **Low-Level Metrics API**: Define custom metrics (counters, histograms, gauges) with minimal overhead — Kamon uses HdrHistogram for accurate percentile calculations
- **Module System**: Enable only the instrumentation modules you need to keep the agent footprint minimal

### Docker Compose with Prometheus + Grafana

Kamon reports to Prometheus, so your deployment focuses on the observability stack:

```yaml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
    restart: unless-stopped

volumes:
  prometheus-data:
  grafana-data:
```

Add Kamon to your Scala/Akka application via `build.sbt`:

```scala
libraryDependencies ++= Seq(
  "io.kamon" %% "kamon-bundle" % "2.7.0",
  "io.kamon" %% "kamon-prometheus" % "2.7.0"
)
```

**Best for**: Teams already using Prometheus/Grafana who want JVM-level metrics and distributed tracing integrated into their existing observability stack.

## Choosing the Right APM for Your Stack

Your choice among these three tools depends on your team's existing infrastructure and monitoring philosophy:

- **Choose Scouter** if you run a multi-instance Java platform and want a centralized APM server with real-time thread monitoring, XLog distributed tracing, and a dedicated web dashboard — similar to a self-hosted Datadog
- **Choose Glowroot** if you want the simplest possible setup with zero infrastructure dependencies and are comfortable with per-JVM dashboards. Perfect for developers who just want to see what their app is doing
- **Choose Kamon** if you already run Prometheus/Grafana and want JVM metrics + distributed tracing integrated into your existing dashboards without a separate APM server

All three tools can coexist in a mature observability stack — Glowroot for deep-dive debugging on individual instances, Scouter for centralized operations monitoring, and Kamon for metrics-driven SLO tracking in Grafana.

## Deployment Architecture Comparison

Understanding how each tool fits into your infrastructure helps with planning:

| Aspect | Scouter | Glowroot | Kamon |
|--------|---------|----------|-------|
| **Agent Footprint** | ~10MB JAR | ~5MB JAR | ~2-5MB per module |
| **Server Requirements** | 2GB+ RAM for collector+server | None (embedded) | Existing Prometheus/Grafana |
| **Network Topology** | Agents → Collector → Server | Agent ↔ Browser | Agent → Prometheus → Grafana |
| **Scaling Model** | Multiple collectors behind LB | Each JVM independent | Prometheus federation |
| **Storage** | Custom scalable DB | Embedded H2 (local) | Prometheus TSDB |

## Why Self-Host Your Java APM?

Running your own APM infrastructure gives you several advantages over SaaS alternatives:

**Data ownership and privacy** is the primary driver. When you monitor production applications, you're collecting detailed information about request patterns, error rates, and sometimes business data embedded in traces. Self-hosted APM keeps this data within your network boundary — no third party sees your transaction payloads or performance profiles.

**Cost predictability** matters at scale. Commercial APM pricing is typically per-host or per-million-spans, which grows linearly with your infrastructure. Once you've provisioned servers for Scouter or Prometheus for Kamon, your monitoring costs are fixed regardless of scale. Teams running 50+ JVM instances can save thousands per month compared to SaaS APM.

**Customization and extensibility** are baked into open-source tools. Scouter's plugin system lets you add business-specific counters that commercial tools would charge extra for. Kamon's module architecture means you instrument exactly what you need without vendor lock-in. For teams with unique monitoring requirements, this flexibility is invaluable.

For broader observability coverage, see our [continuous profiling guide](../2026-04-18-grafana-pyroscope-vs-parca-vs-profefe-self-hosted-continuous-profiling-guide-2026/) for CPU and memory profiling, and our [database monitoring comparison](../2026-04-18-pgwatch2-vs-percona-pmm-vs-pgmonitor-self-hosted-database-monitoring-guide-2026/) for SQL-level insights. If you're building a complete observability platform, our [self-hosted observability platform guide](../2026-04-20-openobserve-vs-quickwit-vs-siglens-self-hosted-observability-guide-2026/) covers log aggregation and metric storage alternatives.

## FAQ

### Does Scouter support non-Java applications?

Scouter has basic support for Node.js and PHP through dedicated agents, but its primary strength is Java/JVM monitoring. The XLog distributed tracing system can propagate context across heterogeneous services if all services use compatible trace headers. For non-Java polyglot environments, Kamon's OpenTelemetry integration offers better cross-language support.

### How does Glowroot handle data persistence across restarts?

Glowroot stores all metrics and traces in an embedded H2 database within the `glowroot/data` directory. This data persists across application restarts. However, each JVM instance stores its own data independently — there's no built-in aggregation across multiple instances. For multi-instance deployments, you'd need to access each instance's Glowroot UI separately (on different ports).

### Can Kamon replace Scouter or Glowroot entirely?

Kamon is a complementary tool, not a direct replacement. While Kamon generates high-quality metrics and traces, it doesn't include its own dashboard — you need Prometheus + Grafana (or a similar stack) to visualize the data. Kamon excels at feeding metrics into existing observability platforms, making it ideal for teams that already have Grafana dashboards and want to add JVM-level detail.

### What's the overhead difference between these tools in production?

Glowroot has the lowest overhead (typically <1% CPU, ~50MB heap), making it safe for production use even on resource-constrained instances. Scouter adds ~2-3% CPU overhead with its agent, plus the collector and server processes (2GB+ RAM). Kamon's overhead varies by module — the core metrics module adds ~1-2% CPU, while full distributed tracing adds an additional ~1-2%. All three are significantly lighter than commercial APM agents.

### Can I use these tools with Spring Boot applications?

Yes, all three tools work with Spring Boot. Scouter provides a Spring Boot starter plugin for automatic configuration. Glowroot's bytecode agent works transparently with any Spring Boot application without additional configuration. Kamon has dedicated `kamon-spring` instrumentation that captures HTTP requests, JDBC queries, and Spring scheduling metrics automatically.

### How do I monitor database queries with these APM tools?

Scouter captures JDBC call timings, SQL text, and connection pool metrics through its built-in DBCP/C3P0/HikariCP plugins — the SQL text appears in XLog traces. Glowroot automatically profiles JDBC calls and shows full SQL statements in transaction traces. Kamon's `kamon-jdbc` module instruments DataSource calls and exports query timing as Prometheus histograms, though it sanitizes SQL text by default for security.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Java APM: Scouter vs Glowroot vs Kamon",
  "description": "Compare three open-source Java application performance monitoring tools: Scouter (enterprise APM), Glowroot (lightweight embedded agent), and Kamon (metrics-first telemetry). Docker Compose configs included.",
  "datePublished": "2026-06-04",
  "dateModified": "2026-06-04",
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
