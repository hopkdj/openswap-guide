---
title: "Metrics Cardinality Is Eating Your Budget: 7 Fixes That Cut Prometheus Storage 80% in 2026"
date: "2026-11-20"
tags: ["prometheus", "observability", "monitoring", "cost-optimization", "metrics"]
draft: false
description: "How to find and kill high-cardinality series in Prometheus, Mimir, Thanos and VictoriaMetrics — with the exact PromQL, relabel configs and limits that cut storage 80%."
---

One engineer adds `user_id` to a request-duration metric as a debugging aid. Nothing breaks. Two weeks later the monitoring stack is ingesting **4.2 million active series**, the Prometheus head block is pinned at 14 GB of RAM, compaction never finishes, and the invoice for the managed metrics backend has gone from €180 to €2,900 a month.

That is not a hypothetical. It is the single most common way self-hosted observability turns into its own outage. The cause is always the same: **cardinality** — the number of unique label combinations — and the fix is never "buy more disk".

## TL;DR

**Find the culprit before you tune anything.** Run `topk(20, count by (__name__)({__name__=~".+"}))` and `promtool tsdb analyze` on an existing block. In nine out of ten stacks, 3–5 metric names own 80% of all series.

**Cut at the source, not at the disk.** `metric_relabel_configs` at scrape time is free and permanent; longer retention is a recurring bill. Dropping one unbounded label typically removes 40–70% of series instantly.

**Replace bucket-spam with native histograms.** A classic histogram with 14 buckets costs 14 series per label set; a native histogram costs one. On a stack with 300 histogram metrics that alone is a 60–90% reduction in histogram series.

**Pre-aggregate what dashboards actually query.** Nobody looks at per-instance latency for 400 pods; they look at p95 per service. A recording rule that drops `pod` and `instance` collapses thousands of series into dozens.

**Then, and only then, set hard limits.** Per-tenant series caps in Mimir turn a silent budget explosion into a visible, bounded rejection you can alert on.

## The Cardinality Math Nobody Shows You

Every series in Prometheus costs RAM in the head block (roughly **3–4 KB** per active series including the WAL index) plus roughly **10–12 KB of compressed storage per day** at a 15-second scrape interval. Multiply that out before you decide a label is "useful":

| Label added to one metric | Series created | RAM in head block | Storage / month | Cost at €0.03/GB-mo |
|---|---|---|---|---|
| `instance` (12 hosts) | 12 | ~48 KB | ~4 MB | negligible |
| `route` (140 endpoints) | 140 | ~560 KB | ~46 MB | €0.001 |
| `status_code` (9 values) | 9 | ~36 KB | ~3 MB | negligible |
| **`user_id` (50,000)** | **50,000** | **~195 MB** | **~16 GB** | **€0.50** |
| **`url` with query strings (unbounded)** | **200,000+** | **~780 MB** | **~65 GB** | **€2.00** |
| **14-bucket histogram × 300 pods** | **4,200** | **~16 MB** | **~1.4 GB** | **€0.04** |
| Full stack after 3 careless labels | 4.2 M | **~14 GB** | **~1.4 TB** | **€42** |

Those per-row numbers look harmless. The last row is the bill: **1.4 TB per month** for a metrics stack serving a 40-person company — and that is the raw-disk price. On a managed backend at €0.20/GB-ingested it becomes €5,800/month, which is exactly how teams end up migrating their metrics backend instead of fixing three label choices.

## Symptom-to-Fix Matrix

| Symptom | What it usually means | Fix |
|---|---|---|
| Head block RAM growing weekly | New label with unbounded values | Drop label at scrape (`metric_relabel_configs`) |
| `prometheus_tsdb_head_series` > 2M on one node | Too many targets × too many labels | Split servers by team, shard by hashmod |
| Compaction never completes, disk alarm | Too many small blocks from churn | Reduce churn first, then tune block ranges |
| Ingestion rejected by remote backend | Tenant series limit hit | Raise limit **and** drop the offending label |
| Dashboards slow, queries time out | High-cardinality aggregation at query time | Recording rules pre-aggregating per service |
| Cardinality spikes after each deploy | Pod/container name labels re-created per rollout | Drop `pod`, use `deployment` + `pod_template_hash` |
| Bill grows but load is flat | Histogram buckets × label sets | Native histograms or fewer buckets |

## 1. Find the Top Offenders in 30 Seconds

Two commands do most of the work. The first ranks metric names by active series; the second inspects an on-disk block and prints the labels responsible.

```promql
# Which metric names own the series count?
topk(20, count by (__name__) ({__name__=~".+"}))

# Which label values explode a single metric?
count by (user_id) ({__name__="http_request_duration_seconds"})
topk(5, count by (url) ({__name__=~"http_.*"}))
```

```bash
# Inspect a persisted block: prints top series by metric and label cardinality
promtool tsdb analyze /var/lib/prometheus --limit=25
promtool tsdb analyze /var/lib/prometheus --extended   # label-value breakdown

# Quick totals from the API instead
curl -s 'http://localhost:9090/api/v1/query?query=prometheus_tsdb_head_series' | jq '.data.result[0].value[1]'
curl -s 'http://localhost:9090/api/v1/label/__name__/values' | jq '.data | length'
```

If the top metric is a histogram, check the bucket count before anything else — that is the cheapest large win on most stacks.

## 2. Drop Labels at Scrape Time (Free and Permanent)

`metric_relabel_configs` runs before the sample is ever appended, so a dropped series costs zero storage forever. This is the highest-leverage config in the entire stack:

```yaml
scrape_configs:
  - job_name: kubernetes-pods
    kubernetes_sd_configs:
      - role: pod
    metric_relabel_configs:
      # Kill per-request identifiers — these belong in logs or exemplars
      - regex: (user_id|session_id|request_id|trace_id|email)
        action: labeldrop
      # Collapse high-churn pod identity into something stable
      - regex: (pod|pod_template_hash|container_id)
        action: labeldrop
      # Drop noisy debug metrics nobody queries
      - source_labels: [__name__]
        regex: 'go_(gc|memstats)_.*|process_open_fds|rest_client_request_duration_seconds_bucket'
        action: drop
      # Keep only the status classes you alert on
      - source_labels: [status_code]
        regex: '2..'
        target_label: status_code
        replacement: '2xx'
        action: replace
```

Three rules of thumb:

- **Anything that identifies a single user, request, or session is not a metric.** Use logs, traces, or exemplars.
- **`pod` is not a stable identity.** Drop it and keep `deployment` plus a hash label; otherwise every rollout re-creates thousands of series.
- **Normalise status codes and paths** before ingestion. `/api/users/8123/orders` and `/api/users/8124/orders` are two series for one endpoint.

## 3. Use Native Histograms Instead of Bucket Explosions

Classic histograms ship one series per bucket. A 14-bucket latency histogram across 300 pods and 4 endpoints is **16,800 series** for one measurement. Native histograms (stable in Prometheus 3.x) store the whole distribution in a single series with sparse buckets:

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  scrape_native_histograms: true
  scrape_classic_histograms: false   # drop classic buckets during migration
```

Before migrating, check the cost of the current histogram series, then compare `histogram_count()`-based quantiles after:

```promql
# How many series are histogram buckets today?
count({__name__=~".*_bucket"})

# Quantiles from native histograms: same answers, ~1/14 the series
histogram_quantile(0.95, sum by (le, service) (rate(http_request_duration_seconds[5m])))
```

Migration caveat: alerting rules written against `_bucket` and `le` need rewriting to `histogram_quantile` over the native type, and older dashboards will show gaps until updated. Do it per job, not all at once.

## 4. Pre-Aggregate With Recording Rules

Most dashboard cardinality comes from grouping dimensions nobody reads. If the question is "p95 latency per service", the per-pod series are pure overhead:

```yaml
groups:
  - name: cardinality-collapse
    interval: 30s
    rules:
      - record: service:http_request_duration_seconds:p95
        expr: histogram_quantile(0.95,
              sum by (service, le) (rate(http_request_duration_seconds_bucket[5m])))
      - record: service:http_requests:rate5m
        expr: sum by (service, status_class) (rate(http_requests_total[5m]))
      # Keep only 1% of raw series for drill-down, delete the rest at scrape
```

Then point dashboards at `service:http_request_duration_seconds:p95` and drop the raw per-pod histograms from ingestion entirely. Typical result on a 300-pod cluster: **raw series from 1.8M to ~90k**, with dashboards faster because every query now hits one aggregated metric instead of 16,800 series.

Our [recording rules management guide](../2026-05-22-self-hosted-prometheus-recording-rules-management-operator-mimir-thanos-guide/) covers keeping these rules maintainable at scale — the operational half of this problem.

## 5. Tier Retention Instead of Extending It

Retention is the line item people reach for first and should reach for last. Raw 15-second samples are only useful for days; weeks-old data is queried at minute granularity.

```yaml
# prometheus.yml — keep raw data short, downsample elsewhere
storage:
  tsdb:
    retention.time: 15d
    retention.size: 60GB
```

Push long-term data to a backend that downscales, and query it through the same endpoint. Thanos, Mimir, Cortex and VictoriaMetrics all handle this differently — the [long-term storage comparison](../2026-04-27-grafana-mimir-vs-thanos-vs-cortex-self-hosted-prometheus-long-term-storage-guide-2026/) covers which one fits which topology. For log-side retention policies (a related but separate bill), see the [log retention lifecycle guide](../2026-05-06-self-hosted-log-retention-lifecycle-management-elasticsearch-ilm-loki-opensearch-ism/).

The arithmetic that matters: dropping 30-day raw retention to 15 days halves the largest storage term, while dropping one bad label can cut it by 70%. **Relabel first, retention second.**

## 6. Set Hard Limits Per Tenant

Limits convert silent growth into a visible rejection. In Mimir:

```yaml
limits:
  max_global_series_per_user: 1500000
  max_label_names_per_series: 25
  max_label_value_length: 512
  ingestion_rate: 80000
  ingestion_burst_size: 150000
  # Per-tenant overrides for the noisy one, not global relief
  # runtime_config file: overrides: {tenant-a: {max_global_series_per_user: 3000000}}
```

Alert on the rejection counters so a limit is a page, not a mystery gap in a graph:

```promql
rate(cortex_discarded_samples_total{reason="per-user-series-limit"}[5m]) > 0
```

Without limits, the noisiest team sets your capacity plan. VictoriaMetrics exposes a built-in cardinality explorer at `/select/vmui/#/cardinality` that ranks labels and values by series count — the fastest way to find the offender when you inherit someone else's stack.

## 7. Filter in the Collector, Not in the Database

If you run OpenTelemetry Collector or Grafana Alloy in front of the backend, drop attributes before the write path:

```yaml
processors:
  transform/drop_high_cardinality:
    metric_statements:
      - context: datapoint
        statements:
          - delete_key(attributes, "user.id") where attributes["user.id"] != nil
          - delete_key(attributes, "http.url") where attributes["http.url"] != nil
          - delete_key(attributes, "net.sock.peer.addr") where attributes["net.sock.peer.addr"] != nil
  metricstransform/drop_debug:
    transforms:
      - include: ^go_gc_.*$
        action: delete
service:
  pipelines:
    metrics:
      receivers: [otlp]
      processors: [transform/drop_high_cardinality, metricstransform/drop_debug, batch]
      exporters: [prometheusremotewrite]
```

This is where a gateway earns its keep: one place to police every team's label hygiene, with the added benefit that the filters are reviewable in Git instead of buried in 400 scrape configs.

## Pitfalls

- **Dropping a label your alerts depend on.** Grep your rule files for every label you plan to drop — `user_id` in a dashboard is noise, but `cluster` in a routing rule is load-bearing.
- **Relabelling after metrics are already stored.** `metric_relabel_configs` only affects new samples. Old series stay until retention expires; expect the graph to fall, not the disk, on day one.
- **Assuming `count(series)` equals cost.** Compressed bytes per sample vary with churn. High-churn series (short-lived pods, request IDs) cost far more per series than steady ones because they create new chunk heads constantly.
- **Pointing many Prometheus servers at one backend without sharding.** Duplicate series get deduplicated only if the HA pairs share external labels; otherwise you pay twice for the same data.
- **Setting limits before fixing labels.** You will page yourself at 3 a.m. for a rejection you caused, on data you did not need to ingest.
- **Forgetting exemplars.** If you drop `trace_id` from metrics, wire exemplars instead — otherwise you lose the ability to jump from a slow bucket to a trace.

## FAQ

**What is a healthy number of active series per Prometheus instance?**
Under **1 million** active series per instance is comfortable on 8–16 GB RAM; 2 million is workable with tuning; beyond 3 million you should shard (`hashmod` on `__address__`) or move to a horizontally scalable backend. RAM usage tracks active series far more than scrape rate.

**Does dropping a label reduce storage retroactively?**
No. Relabelling applies at ingestion. Existing series remain until they exceed `retention.time` or are deleted via the admin API (`POST /api/v1/admin/tsdb/delete_series`, then `POST /api/v1/admin/tsdb/clean_tombstones`). Plan for a one-retention-period lag before disks shrink.

**Are native histograms safe for production in 2026?**
Yes on Prometheus 3.x, with two caveats: alerting rules and dashboards must be rewritten to the native type, and some older remote-write consumers still expect classic buckets. Migrate one job at a time and keep classic histograms enabled for the rest.

**Should I use VictoriaMetrics instead of fixing cardinality?**
Sometimes — VictoriaMetrics handles high-cardinality series with much lower RAM per series, which buys you slack. But it does not fix a `user_id` label; it just makes the same mistake cheaper. Fix the labels first, then pick the backend that matches your query patterns.

**How much can I realistically cut without losing visibility?**
Typical results from the steps above on a mid-size stack: **60–85% fewer active series**, 70–80% less storage, and faster dashboards. The only visibility you actually lose is per-request and per-pod granularity that belongs in logs and traces anyway.

**How do I stop this from happening again in six months?**
Three controls: hard per-tenant series limits with alerting, a CI check that fails pull requests adding labels from a denylist (`user_id`, `request_id`, `email`, `url`), and a weekly `topk` cardinality report posted to the team channel.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Metrics Cardinality Is Eating Your Budget: 7 Fixes That Cut Prometheus Storage 80% in 2026",
  "description": "Find and eliminate high-cardinality series in Prometheus, Mimir, Thanos and VictoriaMetrics with PromQL, relabel configs, native histograms and per-tenant limits.",
  "datePublished": "2026-11-20",
  "dateModified": "2026-11-20",
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
