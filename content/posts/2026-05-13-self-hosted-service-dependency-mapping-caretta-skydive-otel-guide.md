---
title: "Self-Hosted Service Dependency Mapping — Caretta vs Skydive vs OpenTelemetry Service Graph"
date: "2026-05-13"
tags: ["service-dependency", "kubernetes", "observability", "network-topology"]
draft: false
---

When managing complex microservices architectures or large-scale Kubernetes clusters, understanding how services depend on each other is critical for troubleshooting, capacity planning, and incident response. Self-hosted service dependency mapping tools automatically discover, visualize, and track the relationships between your services — without sending sensitive topology data to external SaaS platforms.

## What Is Service Dependency Mapping?

Service dependency mapping is the practice of automatically discovering and visualizing how applications, services, and infrastructure components communicate with each other. Unlike static architecture diagrams that quickly become outdated, dependency mapping tools use real network traffic, service mesh telemetry, or eBPF probes to build live, continuously updated maps of your infrastructure.

Key capabilities of a good dependency mapping tool include:

- **Automatic discovery** — No manual configuration needed; tools detect service relationships from network traffic, DNS queries, or application telemetry
- **Real-time visualization** — Interactive topology maps showing upstream and downstream dependencies
- **Impact analysis** — Understanding which services will be affected when one goes down
- **Integration with observability stacks** — Exporting topology data to Grafana, Prometheus, or other monitoring tools

## Caretta

[Caretta](https://github.com/groundcover-com/caretta) is an open-source Kubernetes service dependency mapper developed by groundcover. It uses eBPF to automatically discover service-to-service communication patterns within a Kubernetes cluster and generates a visual dependency map that can be exported to Grafana.

**Key features:**
- eBPF-based network traffic analysis for zero-overhead discovery
- Automatic generation of Grafana dashboards with service dependency visualizations
- No sidecar or agent injection required — works at the kernel level
- Supports both HTTP/gRPC and TCP-level dependency detection
- Lightweight deployment via Helm chart

**Installation:**
```bash
helm repo add caretta https://groundcover-com.github.io/caretta
helm install caretta caretta/caretta -n monitoring --create-namespace
```

**Docker Compose deployment:**
```yaml
version: "3.8"
services:
  caretta:
    image: ghcr.io/groundcover-com/caretta:latest
    container_name: caretta
    privileged: true
    pid: host
    network_mode: host
    volumes:
      - /sys/kernel/debug:/sys/kernel/debug
      - /var/run/docker.sock:/var/run/docker.sock
    restart: unless-stopped
```

Caretta is ideal for teams running Kubernetes who want a lightweight, eBPF-based dependency mapper that integrates directly with their existing Grafana dashboards.

## Skydive

[Skydive](https://github.com/skydive-project/skydive) is a real-time network topology and protocol analyzer that provides deep visibility into network infrastructure. Originally developed by Red Hat, it captures and analyzes network traffic to build comprehensive topology maps across physical and virtual infrastructure.

**Key features:**
- Real-time topology capture across multi-cloud and hybrid environments
- Protocol analysis for HTTP, DNS, TCP, and custom protocols
- Gremlin-based query language for topology exploration
- Built-in web UI for interactive topology visualization
- Support for OpenStack, Kubernetes, Docker, and bare-metal environments
- Flow tracking with packet-level analysis

**Docker Compose deployment:**
```yaml
version: "3.8"
services:
  skydive-analyzer:
    image: skydive/skydive:latest
    container_name: skydive-analyzer
    command: analyzer
    ports:
      - "8082:8082"
      - "8085:8085"
    environment:
      - SKYDIVE_ANALYZER_LISTEN=0.0.0.0:8082
    restart: unless-stopped

  skydive-agent:
    image: skydive/skydive:latest
    container_name: skydive-agent
    command: agent
    network_mode: host
    pid: host
    environment:
      - SKYDIVE_AGENT_ANALYZERS=skydive-analyzer:8082
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /var/run/openvswitch/db.sock:/var/run/openvswitch/db.sock
    restart: unless-stopped
```

Skydive is suited for organizations that need deep protocol-level analysis alongside topology mapping, especially in hybrid cloud environments with both virtual and physical infrastructure.

## OpenTelemetry Service Graph

The OpenTelemetry Service Graph connector is part of the OpenTelemetry Collector ecosystem. It processes distributed tracing data to automatically generate service dependency graphs from trace spans, making it a natural fit for teams already using OpenTelemetry for observability.

**Key features:**
- Derives dependency graphs from existing OpenTelemetry traces — no additional instrumentation needed
- Integrates with any OTel-compatible collector (Prometheus, Tempo, Jaeger)
- Exports topology data to Prometheus metrics for Grafana visualization
- Supports multi-cluster and multi-tenant environments
- Vendor-neutral and CNCF-hosted

**Collector configuration:**
```yaml
receivers:
  otlp:
    protocols:
      grpc:
      http:

processors:
  servicegraph:
    metrics_exporter: prometheus
    dimensions:
      - http.method
      - db.system

exporters:
  prometheus:
    endpoint: "0.0.0.0:9090"

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [servicegraph]
      exporters: [prometheus]
```

**Docker Compose deployment:**
```yaml
version: "3.8"
services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    container_name: otel-collector
    volumes:
      - ./otel-collector-config.yaml:/etc/otelcol-contrib/config.yaml
    ports:
      - "4317:4317"
      - "4318:4318"
      - "9090:9090"
    restart: unless-stopped
```

The OpenTelemetry Service Graph is the best choice for teams already invested in the OpenTelemetry ecosystem who want to derive dependency maps from their existing tracing data.

## Comparison Table

| Feature | Caretta | Skydive | OpenTelemetry Service Graph |
|---------|---------|---------|----------------------------|
| Primary Focus | K8s dependency mapping | Network topology analysis | Trace-derived dependency graphs |
| Discovery Method | eBPF kernel probes | Traffic capture and analysis | OTel trace spans |
| Deployment | Helm or Docker | Docker or K8s daemonset | OTel Collector |
| Kubernetes Support | Native, cluster-scoped | Multi-cluster | Multi-cluster via collectors |
| Protocol Support | HTTP, gRPC, TCP | HTTP, DNS, TCP, custom | Any OTel-instrumented protocol |
| Visualization | Grafana dashboards | Built-in web UI | Prometheus to Grafana |
| Agent Required | No (eBPF) | Yes (agent per node) | No (uses existing traces) |
| Stars | 2,010+ | 2,787+ | 11,000+ (OTel Collector) |
| License | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| Best For | K8s teams using Grafana | Hybrid cloud networks | OTel observability stacks |

## Why Self-Host Your Service Dependency Mapping?

Service dependency maps contain detailed information about your infrastructure architecture, including internal service names, communication patterns, and data flow paths. This information is highly sensitive from a security perspective — exposing it to external SaaS providers creates an unnecessary attack surface.

Self-hosting dependency mapping tools gives you full control over topology data, ensures maps are available even during network outages to external services, and allows integration with internal observability platforms without cross-organization data sharing. For organizations managing regulated workloads or operating in air-gapped environments, self-hosted dependency mapping is the only viable option.

Additionally, self-hosted tools like Caretta and Skydive operate entirely within your network boundary, meaning dependency discovery data never leaves your infrastructure. This is critical for compliance frameworks that require all observability data to remain on-premises.

For microservices architecture design, see our [service mesh comparison](../2026-04-28-nginx-vs-caddy-vs-envoy-ratelimit-self-hosted-rate-limiting/). If you need deeper network visibility, check our [network traffic analysis guide](../2026-05-06-self-hosted-network-traffic-analysis-ntopng-suricata-zeek/). For Kubernetes monitoring best practices, our [VictoriaMetrics comparison](../prometheus-alertmanager-vs-moira-vs-victoriametrics-vmalert-guide/) covers the fundamentals.


## Deployment Architecture Patterns

Service dependency mapping tools integrate into your observability stack in different ways depending on your infrastructure. Understanding these patterns helps you plan the right architecture for your environment.

**Standalone deployment** is the simplest pattern -- the dependency mapper runs as a single component that collects network traffic or telemetry data and generates visualizations. Caretta follows this model for Kubernetes, deploying as a single DaemonSet that uses eBPF probes to capture service-to-service communication. Skydive requires both an analyzer component and per-node agents, creating a hub-and-spoke topology where agents forward topology data to the central analyzer.

**Sidecar deployment** embeds the dependency mapping logic within each service pod or container. This approach is common with service mesh implementations but adds resource overhead proportional to the number of services. OpenTelemetry Service Graph avoids sidecar overhead by processing traces from a centralized collector rather than running per-service agents.

**Collector-based deployment** uses a centralized data collection layer that aggregates telemetry from multiple sources. This is the OpenTelemetry model -- the Collector receives traces, metrics, and logs from instrumented services, and the Service Graph processor derives topology data from the trace stream. This pattern scales well because the collector can be horizontally scaled independently of the services being monitored.

**Database-backed deployment** stores topology data in a persistent database for historical analysis and trend tracking. Kea DHCP and similar database-backed tools allow you to query historical dependency patterns, identify services that frequently communicate, and detect anomalous communication that might indicate a security issue or misconfiguration.

When planning your deployment architecture, consider the volume of traffic you need to capture, the granularity of dependency data required, and your existing observability infrastructure. Most production environments benefit from starting with a single-tool deployment and expanding as topology data proves valuable for operations.

## FAQ

### What is the difference between service dependency mapping and network topology mapping?

Service dependency mapping focuses on application-level relationships — which service calls which, over what protocol, and with what frequency. Network topology mapping operates at the infrastructure level, showing physical and virtual network connections between hosts, switches, and routers. Both are complementary: dependency maps tell you what services communicate, while topology maps show how the underlying network enables that communication.

### Do service dependency mapping tools require code changes to my applications?

No. Tools like Caretta use eBPF to analyze network traffic at the kernel level without any application modifications. Skydive captures traffic via network interfaces. OpenTelemetry Service Graph derives dependencies from existing trace spans, so if your services already emit OTel traces, no additional instrumentation is needed.

### Can these tools work in air-gapped environments?

Yes. All three tools operate entirely within your infrastructure. Caretta and Skydive analyze local network traffic. OpenTelemetry Service Graph processes traces from your internal collectors. None of them require external connectivity for core functionality.

### How much overhead does eBPF-based dependency mapping add?

eBPF-based tools like Caretta add minimal overhead — typically less than one percent CPU impact — because eBPF programs run in the kernel and avoid context switches to user space. This is significantly lower than sidecar-based approaches which proxy all traffic through an additional process.

### Which tool should I choose for a Kubernetes-only environment?

For Kubernetes-only environments, Caretta is the most purpose-built option. It uses eBPF for zero-overhead discovery, deploys via a single Helm chart, and generates Grafana dashboards out of the box. If you already use OpenTelemetry for tracing, the Service Graph connector is a natural addition with no extra deployment needed.

### Can dependency mapping tools help with incident response?

Absolutely. During an incident, knowing which services depend on a failing component allows you to quickly assess blast radius, prioritize remediation, and communicate impact to stakeholders. Dependency maps also help identify root causes by showing the upstream service that triggered a cascade failure.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Service Dependency Mapping — Caretta vs Skydive vs OpenTelemetry Service Graph",
  "description": "Compare open-source service dependency mapping tools for Kubernetes and hybrid cloud environments. Covers Caretta, Skydive, and OpenTelemetry Service Graph with deployment guides.",
  "datePublished": "2026-05-13",
  "dateModified": "2026-05-13",
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
