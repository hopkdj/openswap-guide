---
title: "Self-Hosted Carbon Accounting Tools: Scaphandre vs CodeCarbon vs Cloud Carbon Footprint"
date: "2026-06-14"
tags: ["carbon-accounting", "sustainability", "green-computing", "devops", "energy-monitoring"]
draft: false
---

## Introduction

As organizations face increasing pressure to measure and reduce their carbon footprint, the need for accurate, self-hosted carbon accounting tools has never been greater. Regulatory frameworks like the EU's Corporate Sustainability Reporting Directive (CSRD) and California's Climate Corporate Data Accountability Act now require detailed emissions reporting, while customers and investors increasingly factor sustainability metrics into their decisions.

Traditional carbon accounting relies on spreadsheets, annual estimates, and third-party consultants — approaches that are expensive, infrequent, and disconnected from real operational data. Modern self-hosted tools take a fundamentally different approach: they measure actual energy consumption in real-time, convert it to carbon emissions using granular grid intensity data, and provide actionable reduction recommendations.

In this guide, we examine three leading open-source carbon accounting platforms: **Scaphandre** (a Prometheus-compatible energy metrology agent), **CodeCarbon** (a lightweight emissions tracker for computational workloads), and **Cloud Carbon Footprint** (a comprehensive multi-cloud carbon analysis tool).

## Comparison Table

| Feature | Scaphandre (1,945⭐) | CodeCarbon (1,857⭐) | Cloud Carbon Footprint (1,040⭐) |
|---------|---------------------|---------------------|--------------------------------|
| **Primary Language** | Rust | Python | TypeScript / Python |
| **Measurement Method** | RAPL / bare-metal power | Hardware + cloud estimates | Cloud billing + estimates |
| **Target Environment** | Bare-metal / VMs | Compute workloads | AWS / GCP / Azure |
| **Prometheus Integration** | Native (metrics endpoint) | Via exporters | Via API |
| **Real-Time Monitoring** | Yes (sub-second) | Per-workload tracking | Daily aggregation |
| **Docker Deployment** | Yes | Yes (compose) | Yes (compose) |
| **Grid Intensity Data** | Electricity Maps API | Built-in regional averages | WattTime / custom |
| **Web Dashboard** | Grafana integration | Dashboard module | Built-in web UI |
| **Carbon Offset Support** | No | Yes (experimental) | Yes (recommendations) |
| **License** | Apache 2.0 | MIT | Apache 2.0 |
| **Last Updated** | May 2026 | June 2026 | April 2026 |

## Scaphandre: Bare-Metal Energy Metering

[Scaphandre](https://github.com/hubblo-org/scaphandre) (1,945 stars) takes a unique approach: instead of estimating emissions from cloud bills or compute time, it measures actual power consumption using Intel RAPL (Running Average Power Limit) — a hardware-level energy counter built into modern CPUs. This gives Scaphandre unprecedented accuracy for bare-metal and virtual machine environments, measuring energy use down to the process and even container level.

**Deploying Scaphandre with Docker:**

```bash
# Run Scaphandre as a Prometheus metrics exporter
docker run -d \
  --name scaphandre \
  --privileged \
  -v /sys/class/powercap:/sys/class/powercap:ro \
  -v /proc:/proc:ro \
  -p 8080:8080 \
  hubblo/scaphandre:latest \
  prometheus --containers

# Verify metrics
curl http://localhost:8080/metrics | grep scaphandre

# Example output:
# scaphandre_host_power_microwatts 45200000
# scaphandre_process_power_consumption_microwatts{pid="1234"} 12500000
```

**Scaphandre with Prometheus and Grafana:**

```yaml
# docker-compose.yml
version: '3.8'

services:
  scaphandre:
    image: hubblo/scaphandre:latest
    privileged: true
    volumes:
      - /sys/class/powercap:/sys/class/powercap:ro
      - /proc:/proc:ro
    command: prometheus
    ports:
      - "8080:8080"

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=secure_admin
```

Scaphandre integrates natively with Prometheus, making it the natural choice for teams already using the Prometheus/Grafana monitoring stack. The Rust implementation is extremely lightweight (~10 MB memory footprint), allowing deployment even on resource-constrained edge servers.

## CodeCarbon: Workload-Level Emissions Tracking

[CodeCarbon](https://github.com/mlco2/codecarbon) (1,857 stars) tracks carbon emissions at the computational workload level — wrapping individual scripts, Jupyter notebooks, or batch jobs and reporting their energy consumption and carbon footprint. This makes it ideal for research teams and data engineering groups who need per-experiment or per-pipeline emissions accounting.

**Integration as a Python Decorator:**

```python
from codecarbon import EmissionsTracker

# Initialize tracker with project name
tracker = EmissionsTracker(
    project_name="monthly_report_generation",
    output_dir="./carbon_logs",
    log_level="info"
)

@tracker.track_emissions
def generate_reports():
    # Your computational workload here
    import pandas as pd
    import numpy as np
    
    df = pd.DataFrame(np.random.randn(1000000, 50))
    df.groupby(0).agg(['mean', 'std', 'sum'])
    return df

# Run with tracking
result = generate_reports()
# Output: [codecarbon INFO] Energy consumed: 0.000342 kWh
#         [codecarbon INFO] CO2 emissions: 0.000152 kgCO2
```

**Docker Compose Deployment with Dashboard:**

```bash
# Clone CodeCarbon
git clone https://github.com/mlco2/codecarbon.git
cd codecarbon

# Start dashboard and API
docker compose up -d

# Dashboard available at http://localhost:8050
# The dashboard shows cumulative emissions, per-project breakdowns,
# and trend charts over time
```

CodeCarbon's dashboard provides clear visualizations of emissions over time, per-project comparisons, and export options for sustainability reporting. The tool also supports experimental carbon offset recommendations, helping teams make informed decisions about neutralizing their computational footprint.

## Cloud Carbon Footprint: Multi-Cloud Emissions Analysis

[Cloud Carbon Footprint](https://github.com/cloud-carbon-footprint/cloud-carbon-footprint) (1,040 stars), originally developed by ThoughtWorks, focuses on estimating carbon emissions from cloud resource usage. It connects to AWS, GCP, and Azure billing APIs to calculate emissions based on actual resource utilization, applying regional carbon intensity factors and embodied emissions estimates for hardware manufacturing.

**Deployment:**

```bash
# Clone and configure
git clone https://github.com/cloud-carbon-footprint/cloud-carbon-footprint.git
cd cloud-carbon-footprint

# Set up environment variables
cat > .env << 'EOF'
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_BILLING_ACCOUNT_ID=your_account_id
GCP_BILLING_PROJECT_ID=your_project
GCP_BIGQUERY_TABLE=your_billing_table
CARBON_EMBODIED_EMISSIONS_ENABLED=true
EOF

# Start with Docker Compose
docker compose up -d

# Access the web UI
# http://localhost:4000
```

**API Query for Carbon Estimates:**

```python
import requests

# Query the Cloud Carbon Footprint API
response = requests.get(
    "http://localhost:4000/api/emissions",
    params={
        "groupBy": "service",
        "startDate": "2026-05-01",
        "endDate": "2026-06-01",
        "cloudProvider": "aws"
    }
)

data = response.json()
for service in data:
    print(f"{service['serviceName']}: {service['co2e']:.2f} kgCO2e")
    print(f"  Cost: ${service['cost']:.2f}")
    print(f"  Region: {service['region']}")
```

## Deployment Strategy for Enterprise Carbon Accounting

A comprehensive carbon accounting deployment typically combines tools at different levels of the stack:

```
┌─────────────────────────────────────────────────┐
│              Carbon Dashboard (Grafana)          │
├─────────────────────────────────────────────────┤
│  Cloud Carbon Footprint  │   CodeCarbon API     │
│  (Cloud resource-level)  │  (Workload tracking) │
├─────────────────────────────────────────────────┤
│              Scaphandre (Infrastructure)         │
│         Prometheus (Metrics collection)          │
├─────────────────────────────────────────────────┤
│        Bare-Metal Servers + Cloud VMs            │
└─────────────────────────────────────────────────┘
```

This layered approach provides granular emissions data: Scaphandre measures actual power draw at the hardware level, CodeCarbon tracks individual computational workloads, and Cloud Carbon Footprint aggregates and analyzes cloud resource usage across providers.

## Why Self-Host Your Carbon Accounting Infrastructure?

Carbon accounting data is increasingly business-critical and regulated. The EU's CSRD mandates auditable emissions reporting with the same rigor as financial statements. Self-hosting your carbon accounting tools ensures that your emissions data — which reveals operational patterns, computational intensity, and infrastructure details — remains under your organization's data governance policies rather than being stored on third-party SaaS platforms.

Second, **accuracy matters**. Cloud provider carbon calculators typically use annual average grid intensity factors and may lag months behind on regional data updates. Self-hosted tools like Scaphandre with real-time Electricity Maps API integration can provide hourly carbon intensity data, enabling carbon-aware scheduling that shifts workloads to times of day when the grid is cleanest. For a complementary view on energy systems, see our [home energy monitoring guide](../2026-05-02-self-hosted-home-energy-monitoring-platforms-guide/) and our [solar energy monitoring comparison](../2026-06-05-self-hosted-solar-energy-monitoring-openems-emoncms-guide/).

Third, the **cost predictability** of self-hosting becomes compelling at enterprise scale. Cloud-based carbon accounting SaaS products typically charge per resource or per metric — costs that scale linearly with infrastructure. A dedicated server running the open-source toolchain described above can monitor thousands of resources at a flat monthly cost. For additional sustainable computing infrastructure, see our guide to [building energy modeling platforms](../2026-06-12-self-hosted-building-energy-modeling-energyplus-openstudio-spawn-guide/).

## FAQ

### How accurate are these carbon estimates compared to direct power meter readings?

Scaphandre's RAPL-based measurements have been validated against external power meters with ±5% accuracy on Intel processors. CodeCarbon and Cloud Carbon Footprint use estimation models that are typically accurate to ±15-25% depending on data center efficiency factors and regional grid assumptions. For regulatory-grade reporting, Scaphandre with hardware-level metering is the most defensible approach.

### Can these tools track emissions from GPU workloads?

Scaphandre can track NVIDIA GPU power consumption through the NVML interface. CodeCarbon has experimental GPU tracking support through pynvml. Cloud Carbon Footprint does not currently provide GPU-specific estimates but includes GPU instances in its cloud billing analysis. For GPU-heavy HPC environments, combining Scaphandre with GPU-level monitoring provides the most complete picture.

### How do I integrate carbon data into existing DevOps dashboards?

Scaphandre's Prometheus-native design makes it trivial to add carbon metrics to existing Grafana dashboards alongside CPU, memory, and network metrics. CodeCarbon provides a JSON API and CSV export for integration with data warehouses. Cloud Carbon Footprint exports via its REST API and can feed into BI tools like Metabase or Apache Superset.

### What's the best tool for a small startup versus a large enterprise?

Small teams (5-50 people) benefit most from CodeCarbon's simplicity — install the Python package, wrap your key scripts, and get immediate per-experiment emissions data. Mid-size organizations (50-500) should deploy Scaphandre with Prometheus/Grafana for continuous infrastructure monitoring. Large enterprises with multi-cloud environments should deploy all three in the layered architecture described above, with Cloud Carbon Footprint providing the executive-level cloud emissions dashboard.

### Can I use these tools for Scope 3 emissions reporting?

Cloud Carbon Footprint is explicitly designed for Scope 2 (purchased electricity) and partial Scope 3 (cloud provider upstream emissions) reporting. CodeCarbon can contribute to Scope 3 category 1 (purchased goods and services) by tracking computational carbon in outsourced data processing contracts. For full Scope 3 reporting across your supply chain, you'll need to combine these tools with supplier-specific emissions data and lifecycle assessment databases.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Carbon Accounting Tools: Scaphandre vs CodeCarbon vs Cloud Carbon Footprint",
  "description": "Compare open-source carbon accounting for IT infrastructure: Scaphandre (1,945 stars) for hardware-level metering, CodeCarbon (1,857 stars) for workload tracking, and Cloud Carbon Footprint (1,040 stars) for multi-cloud analysis. Includes Docker deployment, Prometheus integration, and enterprise architecture.",
  "datePublished": "2026-06-14",
  "dateModified": "2026-06-14",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
