---
title: "Self-Hosted Frontend Observability: Grafana Faro vs Highlight.io vs OpenTelemetry Web SDK"
date: "2026-05-07"
draft: false
tags: ["monitoring", "observability", "frontend", "web-performance", "grafana", "opentelemetry"]
description: "Compare open-source frontend observability tools — Grafana Faro, Highlight.io, and OpenTelemetry Web SDK — for self-hosted real user monitoring (RUM) and web application performance tracking."
---

Frontend observability has become critical for teams running self-hosted web applications. While backend APM tools like Signoz, HyperDX, and Coroot monitor server-side performance, understanding how users actually experience your application requires dedicated frontend telemetry collection. This guide compares three open-source approaches to frontend observability: **Grafana Faro**, **Highlight.io**, and the **OpenTelemetry Web SDK**.

## What Is Frontend Observability?

Frontend observability (also called Real User Monitoring or RUM) involves collecting telemetry data directly from users' browsers — page load times, JavaScript errors, network request failures, Core Web Vitals, and user session flows. Unlike synthetic monitoring (which tests from fixed locations), RUM captures real-world performance across all user devices, networks, and geographic regions.

Self-hosting frontend observability tools gives you complete control over collected telemetry data. This matters for compliance with GDPR, HIPAA, and other privacy regulations where user interaction data must remain on your infrastructure. It also eliminates the per-session or per-event pricing models of commercial RUM SaaS platforms.

## Grafana Faro Web SDK

[Grafana Faro](https://github.com/grafana/faro) is Grafana Labs' open-source frontend observability SDK. It provides a highly configurable web SDK that instruments browser applications to capture performance metrics, errors, logs, and traces, then ships them to a Grafana Cloud or self-hosted Grafana stack via the Faro Collector.

**Key features:**

- Automatic Core Web Vitals collection (LCP, FID, CLS, INP)
- JavaScript error tracking with stack traces
- Web Vitals and navigation timing APIs
- OpenTelemetry-compatible data format
- Integration with Grafana Loki, Tempo, and Prometheus
- Custom event and metric instrumentation

**Architecture:** Faro runs as a JavaScript SDK embedded in your web application. It batches telemetry data and sends it to the Faro Collector (a Go-based service), which transforms the data into OpenTelemetry format and forwards it to your Grafana backend.

```yaml
# Docker Compose for Faro Collector
services:
  faro-collector:
    image: grafana/faro-collector:latest
    ports:
      - "12347:12347"
    environment:
      - FARO_COLLECTOR_OTLP_ENDPOINT=http://tempo:4318
      - FARO_COLLECTOR_LOKI_ENDPOINT=http://loki:3100
    depends_on:
      - tempo
      - loki

  tempo:
    image: grafana/tempo:latest
    ports:
      - "4318:4318"
    volumes:
      - ./tempo-config.yaml:/etc/tempo/config.yaml

  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yaml:/etc/loki/config.yaml
```

```javascript
// Frontend integration
import { initializeFaro } from '@grafana/faro-web-sdk';

initializeFaro({
  url: 'https://faro-collector.yourdomain.com/collect',
  app: {
    name: 'my-web-app',
    version: '1.0.0',
  },
  instrumentations: [
    getBrowserMetricsInstrumentation(),
    getConsoleInstrumentation(),
    getErrorsInstrumentation(),
    getWebVitalsInstrumentation(),
  ],
});
```

## Highlight.io

[Highlight.io](https://github.com/highlight/highlight) is an open-source, full-stack monitoring platform that combines error monitoring, session replay, logging, distributed tracing, and frontend observability into a single self-hosted deployment. With over 10,000 GitHub stars, it is one of the most popular open-source alternatives to commercial monitoring suites.

**Key features:**

- Session replay with DOM recording
- Frontend error tracking and console capture
- Backend error monitoring via SDK integrations
- Distributed tracing (OpenTelemetry compatible)
- Log aggregation and forwarding
- Performance metrics and Core Web Vitals
- User identification and tagging

**Architecture:** Highlight.io deploys as a full-stack application with a frontend dashboard, backend API, PostgreSQL database, and ClickHouse for high-volume telemetry storage. The frontend SDK records user sessions and performance data, sending it to your self-hosted backend.

```yaml
# Docker Compose for Highlight.io
services:
  frontend:
    image: highlight/front-end:latest
    ports:
      - "8080:8080"
    environment:
      - BACKEND_URL=http://backend:8082
      - PUBLIC_OTEL_COLLECTOR_URL=http://otel-collector:4318
    depends_on:
      - backend
      - otel-collector

  backend:
    image: highlight/back-end:latest
    ports:
      - "8082:8082"
      - "8083:8083"
    environment:
      - FRONTEND_HOST=http://frontend:8080
      - POSTGRES_HOST=postgres
      - CLICKHOUSE_HOST=clickhouse
      - MINIO_HOST=minio
    depends_on:
      - postgres
      - clickhouse
      - minio

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_USER=highlight
      - POSTGRES_PASSWORD=highlight-secret
      - POSTGRES_DB=highlight

  clickhouse:
    image: clickhouse/clickhouse-server:latest
    volumes:
      - clickhouse-data:/var/lib/clickhouse

  minio:
    image: minio/minio:latest
    command: server /data
    volumes:
      - minio-data:/data

  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    ports:
      - "4318:4318"
    volumes:
      - ./otel-config.yaml:/etc/otel/config.yaml

volumes:
  clickhouse-data:
  minio-data:
```

## OpenTelemetry Web SDK

The [OpenTelemetry JavaScript SDK](https://github.com/open-telemetry/opentelemetry-js) provides a vendor-neutral, open-source framework for collecting frontend telemetry data. As part of the broader OpenTelemetry project, it offers standardized instrumentation for web applications that can export data to any OTLP-compatible backend.

**Key features:**

- Vendor-neutral, CNCF-standardized instrumentation
- Automatic page load and resource timing capture
- XMLHttpRequest and Fetch API tracing
- Custom span and event creation
- Export to any OTLP-compatible backend
- Large ecosystem of community plugins
- Web Vitals integration via `@opentelemetry/instrumentation-document-load`

**Architecture:** The OTel Web SDK runs in the browser as a JavaScript library. It captures telemetry data and exports it via OTLP over HTTP to any compatible backend — Grafana Tempo, Jaeger, SigNoz, or a custom OpenTelemetry Collector deployment.

```yaml
# Docker Compose for OpenTelemetry Collector + Backend
services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    ports:
      - "4318:4318"  # OTLP HTTP receiver
    volumes:
      - ./otel-collector-config.yaml:/etc/otelcol/config.yaml
    depends_on:
      - tempo

  tempo:
    image: grafana/tempo:latest
    ports:
      - "3200:3200"
    volumes:
      - tempo-data:/tmp/tempo

volumes:
  tempo-data:
```

```yaml
# OpenTelemetry Collector config
receivers:
  otlp:
    protocols:
      http:
        endpoint: "0.0.0.0:4318"

processors:
  batch:

exporters:
  otlp:
    endpoint: "tempo:4318"
    tls:
      insecure: true

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlp]
```

```javascript
// OTel Web SDK integration
import { WebTracerProvider } from '@opentelemetry/sdk-trace-web';
import { registerInstrumentations } from '@opentelemetry/instrumentation';
import { getWebAutoInstrumentations } from '@opentelemetry/auto-instrumentations-web';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-base';

const provider = new WebTracerProvider({
  spanProcessors: [
    new BatchSpanProcessor(
      new OTLPTraceExporter({ url: 'https://otel-collector.yourdomain.com/v1/traces' })
    ),
  ],
});

provider.register();

registerInstrumentations({
  instrumentations: [
    getWebAutoInstrumentations({
      '@opentelemetry/instrumentation-document-load': { enabled: true },
      '@opentelemetry/instrumentation-fetch': { enabled: true },
      '@opentelemetry/instrumentation-xml-http-request': { enabled: true },
    }),
  ],
});
```

## Comparison Table

| Feature | Grafana Faro | Highlight.io | OpenTelemetry Web SDK |
|---------|-------------|-------------|----------------------|
| **License** | AGPL-3.0 | MIT | Apache 2.0 |
| **GitHub Stars** | 300+ | 10,000+ | 3,370+ |
| **Session Replay** | No | Yes (DOM recording) | No |
| **Core Web Vitals** | Yes (built-in) | Yes (built-in) | Yes (via plugin) |
| **Error Tracking** | Yes | Yes | Yes (via spans) |
| **Backend Integration** | Grafana stack only | Built-in full-stack | Any OTLP backend |
| **Data Format** | Custom → OTLP | OTLP | Native OTLP |
| **Self-Hosted Backend** | Faro Collector | Full platform | OTel Collector |
| **Database Required** | None (forwarder only) | PostgreSQL + ClickHouse | Depends on backend |
| **Vendor Lock-in** | High (Grafana ecosystem) | Low (open platform) | None (CNCF standard) |
| **Deployment Complexity** | Low | High (multiple services) | Medium |
| **Custom Instrumentation** | Yes | Yes | Yes (extensive API) |

## Choosing the Right Frontend Observability Tool

**Choose Grafana Faro if** you already run a Grafana stack (Loki, Tempo, Prometheus) and want tightly integrated frontend telemetry. Faro's data pipeline is purpose-built for the Grafana ecosystem, making it the lowest-friction option for Grafana users. The trade-off is vendor lock-in — Faro sends data exclusively to Grafana backends.

**Choose Highlight.io if** you want a comprehensive, all-in-one monitoring platform that combines frontend RUM, session replay, backend error tracking, and distributed tracing. Highlight.io is the most feature-complete open-source alternative to commercial platforms like Datadog RUM or New Relic Browser. The trade-off is operational complexity — deploying PostgreSQL, ClickHouse, MinIO, and multiple services requires significant infrastructure.

**Choose OpenTelemetry Web SDK if** you want maximum flexibility and zero vendor lock-in. As a CNCF standard, OTel lets you export telemetry data to any compatible backend — Grafana, Jaeger, SigNoz, or a custom solution. It is the best choice for teams already invested in OpenTelemetry across their full-stack observability pipeline. The trade-off is that you must assemble your own backend infrastructure and session replay is not included.

## Why Self-Host Frontend Observability?

Self-hosting frontend observability tools offers significant advantages over commercial SaaS RUM platforms:

**Data sovereignty and compliance:** User interaction data — page views, click patterns, form inputs, error traces — often falls under GDPR, CCPA, and other privacy regulations. Self-hosting ensures this data never leaves your infrastructure, eliminating compliance risk and third-party data processing agreements. For organizations in regulated industries (finance, healthcare, government), this is a hard requirement.

**Cost control at scale:** Commercial RUM platforms typically charge per session, per event, or per GB of telemetry data. For high-traffic applications processing millions of page views monthly, these costs can exceed $1,000-$5,000/month. Self-hosted alternatives use your existing infrastructure — the marginal cost of additional telemetry volume is essentially zero beyond storage and compute.

**No data sampling:** Commercial platforms often sample or truncate data at high volumes to control costs. Self-hosted tools process 100% of telemetry data, ensuring you never miss critical errors or performance regressions because they fell outside the sampling window.

**Custom retention policies:** Commercial platforms enforce fixed retention periods (typically 7-30 days for detailed data). Self-hosted tools let you define custom retention — keep detailed session data for 90 days, aggregate metrics for a year, or store raw traces indefinitely for compliance audits.

For teams managing backend observability, our [complete observability comparison](../2026-04-20-openobserve-vs-quickwit-vs-siglens-self-hosted-observability-guide-2026/) covers self-hosted alternatives for logging and tracing. If you also need web performance testing from synthetic vantage points, our [web performance monitoring guide](../2026-04-21-sitespeedio-vs-webpagetest-vs-lighthouse-self-hosted-web-performance-monitoring-2026/) compares tools for automated performance audits.

## FAQ

### What is the difference between RUM and synthetic monitoring?

Real User Monitoring (RUM) captures performance data from actual users visiting your application — their devices, networks, and geographic locations. Synthetic monitoring tests your application from fixed, controlled locations using automated scripts. RUM tells you how real users experience your app; synthetic monitoring tells you whether your app is up and performing within SLAs from specific vantage points. Both are complementary and should be used together.

### Can I use OpenTelemetry Web SDK with Grafana?

Yes. The OpenTelemetry Web SDK exports data in OTLP format, which Grafana Tempo accepts natively. You can run an OpenTelemetry Collector as an intermediary to transform, batch, and route the data to Tempo, Loki, or Prometheus. This gives you the flexibility of OTel instrumentation with Grafana's visualization and alerting capabilities.

### Does Grafana Faro support session replay?

No. Grafana Faro focuses on metrics, errors, logs, and traces — it does not record user sessions or DOM interactions. If session replay is a requirement, Highlight.io provides built-in session recording with DOM-level fidelity. Alternatively, you can pair Faro with a dedicated session replay tool like OpenReplay.

### How much storage does self-hosted Highlight.io require?

Highlight.io uses ClickHouse for high-volume telemetry storage and PostgreSQL for application metadata. For a moderate-traffic application (10,000 sessions/day), expect approximately 5-10 GB/day of ClickHouse storage for session replay data, plus ~500 MB/day for metrics and traces. ClickHouse compresses data efficiently, so actual disk usage is typically 50-70% lower than raw data volume. Plan for at least 100 GB of persistent storage for a month of retention.

### Which frontend observability tool has the lowest overhead?

The OpenTelemetry Web SDK has the smallest JavaScript bundle size (~15-30 KB gzipped for core instrumentation) and minimal runtime overhead. Grafana Faro is slightly larger (~40-50 KB) due to its custom data pipeline. Highlight.io's SDK is the largest (~80-100 KB) because it includes session replay recording capabilities. All three tools use batching and asynchronous sending to minimize impact on page load performance.

### Can I migrate from a commercial RUM platform to a self-hosted tool?

Migration depends on the commercial platform's data export capabilities. Most SaaS RUM tools (Datadog RUM, New Relic Browser, Splunk RUM) do not provide historical data export. You can switch your instrumentation to a self-hosted tool going forward, but historical data will remain in the commercial platform. Plan for a parallel run period where both tools collect data simultaneously, then decommission the commercial platform once sufficient historical data has accumulated in your self-hosted system.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Frontend Observability: Grafana Faro vs Highlight.io vs OpenTelemetry Web SDK",
  "description": "Compare open-source frontend observability tools for self-hosted real user monitoring and web application performance tracking.",
  "datePublished": "2026-05-07",
  "dateModified": "2026-05-07",
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
