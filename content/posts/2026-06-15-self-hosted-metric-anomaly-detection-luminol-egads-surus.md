---
title: "Self-Hosted Metric Anomaly Detection: Luminol vs EGADS vs Surus"
date: "2026-06-15"
tags: ["monitoring", "observability", "devops", "anomaly-detection", "metrics", "time-series", "alerting"]
draft: false
---

## Introduction

Modern infrastructure generates millions of metrics every minute — CPU utilization, request latency, error rates, queue depths, and hundreds more. Manually setting static alert thresholds ("alert if CPU > 80%") breaks down at scale because what's normal at 2 PM on Tuesday differs dramatically from normal at 3 AM on Sunday.

Metric anomaly detection solves this by automatically learning what "normal" looks like for each metric and alerting on statistically significant deviations. Instead of maintaining thousands of static thresholds, operations teams deploy anomaly detection that adapts to seasonal patterns, trend changes, and infrastructure growth.

This guide compares three battle-tested open-source metric anomaly detection frameworks — **Luminol** (LinkedIn), **EGADS** (Yahoo), and **Surus** (Netflix) — covering their detection algorithms, integration patterns, and deployment strategies.

## Comparison: Luminol vs EGADS vs Surus

| Feature | Luminol | EGADS | Surus |
|---------|---------|-------|-------|
| **Developer** | LinkedIn | Yahoo | Netflix |
| **Language** | Python | Java | Java |
| **GitHub Stars** | 1,229 | 1,189 | 462 |
| **Core Algorithms** | Bitmap distance, exp smoothing, spectral residual | Olympic scoring, Kalman filter, moving average | PCA, Robust PCA, SVD |
| **Seasonal Detection** | Yes (configurable) | Yes (time-series aware) | No (point anomaly focus) |
| **Correlation Engine** | Yes (cross-metric) | Limited | No |
| **Time Series DB Integration** | Plugin-based | InfluxDB native | File/CSV based |
| **Output** | JSON anomaly reports | JSON + dashboard | JSON + scores |
| **Last Update** | August 2025 | November 2023 | March 2023 |
| **License** | BSD-2 | BSD-3 | Apache 2.0 |
| **Docker Support** | Community images | Official | Community |

## How Metric Anomaly Detection Works

### Luminol: Correlation-Aware Detection

Developed by LinkedIn's site reliability team, Luminol goes beyond simple threshold-based anomaly detection with a multi-algorithm approach. It computes an anomaly score using four complementary methods:

- **Exponential Moving Average**: Tracks trend shifts
- **Spectral Residual**: Identifies frequency-domain anomalies
- **Bitmap Distance**: Compares time windows for pattern changes
- **Histogram distance**: Detects distribution shifts

Luminol's standout feature is its **correlation engine** — when it detects an anomaly in one metric, it automatically looks for correlated anomalies in related metrics. This helps distinguish real incidents (multiple correlated anomalies) from isolated noise (single metric spike).

**Installation and usage:**

```bash
# Install via pip
pip install luminol

# Basic anomaly detection script
python3 << 'EOF'
from luminol.anomaly_detector import AnomalyDetector
from luminol.correlator import Correlator

# Load time series data
ts_data = {
    'cpu_usage': [(1466000000, 45.2), (1466000060, 46.1), ...],
    'request_latency': [(1466000000, 120.5), (1466000060, 122.1), ...],
}

# Detect anomalies
detector = AnomalyDetector(ts_data['cpu_usage'])
anomalies = detector.get_anomalies()

# Find correlated anomalies
correlator = Correlator(ts_data)
correlations = correlator.get_correlated_anomalies()
for ts, score in correlations:
    print(f"Correlated: {ts} (score: {score})")
EOF
```

**Docker deployment:**

```bash
# Run Luminol analysis in a container
docker run -v $(pwd)/data:/data python:3.11-slim sh -c \
  "pip install luminol && python3 /data/analyze.py"
```

### EGADS: The Pluggable Framework

Yahoo's EGADS (Extensible Generic Anomaly Detection System) separates anomaly detection into two pluggable components: a **time series forecasting model** and an **anomaly detection model**. This modular architecture means you can mix and match forecasting engines (Olympic scoring, Kalman filter, DOUBLE exponential smoothing) with detection models (threshold, KSigma, adaptive kernel density).

EGADS was built for Yahoo's massive infrastructure and handles millions of metrics per minute. It integrates natively with time series databases and includes both a Java library and a REST API server.

**Installation and usage:**

```bash
# Clone and build
git clone https://github.com/yahoo/egads.git
cd egads
mvn clean package -DskipTests

# Run detection via CLI
java -cp target/egads-0.5.0-jar-with-dependencies.jar \
  com.yahoo.egads.Egads \
  -f /path/to/metrics.csv \
  -c config.ini
```

**Configuration example (config.ini):**

```ini
# EGADS configuration
INPUT=input.csv
OUTPUT=output.csv

# Time series model
TS_MODEL=OlympicModel
PERIOD=168
WINDOW_SIZE=336

# Anomaly detection model
AD_MODEL=KSigmaModel
KSIGMA_THRESHOLD=3.0

# Aggregation
AGGREGATION=Average
OP_TYPE=DETECT_ANOMALY
```

### Surus: PCA-Based Anomaly Scoring

Netflix's Surus takes a fundamentally different approach. Instead of modeling individual time series, Surus applies **dimensionality reduction** (PCA — Principal Component Analysis) across multiple metrics simultaneously. This technique is particularly effective at detecting subtle anomalies that would be invisible when looking at metrics individually.

Surus computes a single anomaly score per time window by measuring how far the current metric vector deviates from the principal components learned during training. A high anomaly score indicates the current infrastructure state is "unusual" in a statistically meaningful way.

**Installation and usage:**

```bash
# Clone and build
git clone https://github.com/netflix/surus.git
cd surus
mvn clean package

# Run PCA-based anomaly detection
java -cp target/surus-1.0-SNAPSHOT.jar \
  com.netflix.surus.anomaly.AnomalyDetector \
  --input metrics.csv \
  --components 3 \
  --threshold 3.0
```

## Integrating with Your Monitoring Stack

All three tools produce JSON output that can be consumed by your existing monitoring stack. The typical integration pattern:

```yaml
# Prometheus Alertmanager integration concept
# 1. Collect metrics → 2. Run anomaly detection → 3. Feed results to alerting

groups:
  - name: anomaly_alerts
    rules:
      - alert: AnomalyDetected
        expr: anomaly_score{job="luminol"} > 3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Anomaly detected in {{ $labels.metric }}"
          description: "Metric {{ $labels.metric }} has anomaly score {{ $value }}"
```

For teams running comprehensive monitoring infrastructure, our [self-hosted continuous profiling guide](../2026-04-18-grafana-pyroscope-vs-parca-vs-profefe-self-hosted-continuous-profiling-guide-2026/) complements anomaly detection with code-level performance insights. Our [database monitoring comparison](../2026-04-18-pgwatch2-vs-percona-pmm-vs-pgmonitor-self-hosted-database-monitoring-guide-2026/) covers monitoring specific to database workloads where anomaly detection is especially valuable.

For the broader observability picture, see our [self-hosted observability platform guide](../2026-04-20-openobserve-vs-quickwit-vs-siglens-self-hosted-observability-guide-2026/) for building a complete monitoring pipeline from metrics collection to visualization.

## Choosing the Right Anomaly Detection Tool

- **Luminol** is best for teams that need cross-metric correlation. Its ability to connect anomalies across different signals helps reduce alert fatigue. Choose Luminol when you have diverse metrics (application, infrastructure, business) and want automatic root cause correlation. The Python ecosystem makes it easy to extend.

- **EGADS** is ideal for large-scale time series environments where you need flexible algorithm selection. Its modular design lets you experiment with different model combinations without rewriting code. Choose EGADS when you have high metric cardinality (thousands of unique time series) and need production-hardened forecasting.

- **Surus** excels at infrastructure-wide anomaly detection where a multi-dimensional view matters more than per-metric analysis. Its PCA approach naturally handles correlated metrics and detects cluster-level anomalies that single-series methods miss. Choose Surus when you need infrastructure health scoring rather than per-metric alerting.


## Deployment Architecture and Scaling Considerations

When deploying anomaly detection in production, the architecture you choose depends on your metric volume and latency requirements. For small to medium deployments (under 10,000 unique metrics), a single-instance setup running Luminol or EGADS on a 4-core VM with 16 GB RAM is sufficient. Process metrics in 5-minute batches, store anomaly results in a time series database, and configure alerts based on anomaly scores.

For larger deployments with hundreds of thousands of metrics, a distributed architecture becomes necessary. EGADS was specifically designed for this scale at Yahoo, where it processes millions of metrics per minute. The recommended pattern uses a message queue (Kafka or Redis Streams) to fan out metrics to multiple worker instances, each processing a subset of the metric space. Results are aggregated by a central scoring service that normalizes anomaly scores across workers before pushing to alerting systems.

Luminol's correlation engine adds an important architectural consideration: it needs access to multiple related metrics to compute correlations, which means metrics should be grouped by service or subsystem on the same worker. For example, all metrics from the payments service should be processed together so that correlated anomalies between payment latency and payment error rate can be detected. If these metrics are split across workers, correlation analysis becomes an expensive cross-worker join operation.

Memory management is another critical factor. EGADS maintains in-memory time series windows for forecasting, typically 1-4 weeks of data per metric. At 100,000 metrics with hourly resolution, this requires roughly 50-100 GB of RAM. Luminol's bitmap-based approach is more memory-efficient, using compressed time window representations that require 60-70% less memory for equivalent time ranges. Surus's PCA approach is the most memory-efficient since it reduces the dimensionality of the metric space before analysis — the principal component matrix for 50,000 metrics can fit in under 2 GB.

For teams just getting started, we recommend deploying Luminol in a Docker container attached to your existing Prometheus or InfluxDB instance, running in shadow mode (log-only, no alerts) for 2-4 weeks while you tune parameters and validate results. Once you're confident in the anomaly detection quality, enable alerting gradually — starting with high-severity production services before expanding to development and staging environments.


## FAQ

### How is anomaly detection different from threshold-based alerting?

Threshold-based alerting uses fixed rules (CPU > 80%, latency > 500ms) that require manual configuration and don't adapt to changing baselines. Anomaly detection learns normal patterns from historical data and alerts on statistically significant deviations — so a 40% CPU spike at 3 AM triggers an alert while the same spike during a known batch job doesn't.

### What's the minimum data history needed for effective anomaly detection?

For daily seasonal patterns, 2-4 weeks of data is sufficient for basic detection. For weekly patterns (weekend vs weekday), 4-8 weeks provides reliable baselines. EGADS and Luminol can start producing useful results with as little as 1 week of data, but accuracy improves significantly with longer training periods.

### Do these tools handle gaps in metric data?

EGADS has built-in interpolation for missing data points. Luminol handles gaps gracefully through its bitmap comparison approach. Surus requires complete data matrices — gaps must be filled or imputed before processing. Plan your data collection pipeline to minimize metric gaps for best results.

### Can I use these tools for business metrics, not just infrastructure?

Yes. Luminol and EGADS are metric-agnostic — they analyze any numerical time series regardless of source. You can apply anomaly detection to business metrics like transaction volumes, user signups, revenue, or API usage patterns. The statistical methods are the same whether you're analyzing CPU temperature or daily active users.

### How do I reduce false positives from anomaly detection?

Start with higher anomaly thresholds (3-4 standard deviations) and gradually lower them as you validate results. Configure alert suppression windows during known maintenance periods. Use Luminol's correlation engine to verify anomalies against related metrics before alerting. Run detection tools in "shadow mode" (log-only, no alerts) for 2-3 weeks to tune parameters before enabling production alerts.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Metric Anomaly Detection: Luminol vs EGADS vs Surus",
  "description": "Compare three production-grade open-source metric anomaly detection frameworks — LinkedIn Luminol, Yahoo EGADS, and Netflix Surus — for detecting anomalies in infrastructure and application metrics.",
  "datePublished": "2026-06-15",
  "dateModified": "2026-06-15",
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
