---
title: "Go Metrics in 2026: prometheus/client_golang vs OpenTelemetry Go vs VictoriaMetrics/metrics"
date: "2026-10-24"
tags: ["go", "observability", "prometheus", "opentelemetry", "metrics", "monitoring"]
draft: false
cover: "/img/screenshots/prometheus-go-metrics.jpg"
description: "A hands-on comparison of the three Go metrics libraries that matter in 2026: instrumentation API, cardinality control, histogram cost, and migration paths."
---

A single careless label turned a healthy Go service into a monitoring incident last quarter: someone added `user_id` to a request counter, the metric fanned out to roughly 400,000 active series, and the scrape target started timing out before the on-call engineer even opened the dashboard. The application was fine. The *instrumentation* was not. That is the moment most teams discover that the metrics library they picked in 2019 is now a load-bearing architectural decision.

Go has three credible answers in 2026: **prometheus/client_golang** (the classic), **OpenTelemetry Go** (the vendor-neutral standard), and **VictoriaMetrics/metrics** (the allocation-obsessed outlier). They are not interchangeable, and the differences show up in exactly the places that hurt in production: label cardinality, histogram memory, and how much work you do on the hot path of every request.

## TL;DR / Quick Verdict

- **Pick `prometheus/client_golang`** if you run Prometheus or any Prometheus-compatible backend and want the smallest possible diff from the ecosystem's defaults. It is boring, battle-tested, and every Grafana dashboard tutorial already assumes it.
- **Pick OpenTelemetry Go** if you need traces, logs and metrics from one SDK, or if your organization has standardized on OTLP. Accept that you will write more setup code and pay more per metric update.
- **Pick `VictoriaMetrics/metrics`** if you are pushing to VictoriaMetrics and your hot path is allocation-sensitive — queue workers, proxies, high-RPS gateways. Do not pick it if you need Prometheus-native classic histograms or exemplars.
- **Do not migrate just for fashion.** A working `client_golang` setup scraped by a collector is already OTLP-compatible at the pipeline level. Migrate the SDK when you need tracing correlation or per-attribute cardinality limits, not because a conference talk said so.

## The Three Libraries at a Glance

Live repository data, pulled at publish time:

| Dimension | prometheus/client_golang | OpenTelemetry Go | VictoriaMetrics/metrics |
|---|---|---|---|
| GitHub stars | 6,043 | 6,582 | 710 |
| Last commit | 2026-10-23 | 2026-10-23 | 2026-09-28 |
| Primary API style | Global registry + collectors | Meter / instrument objects | Package-level named metrics |
| Native histograms | Yes (classic + native) | Explicit bucket advice via Views | VictoriaMetrics `vmrange` only |
| Exemplars | Yes | Yes (via exporter) | No |
| OTLP push | Via bridge/collector scrape | Native (HTTP + gRPC) | No (Prometheus text or VM push) |
| Cardinality guardrails | Manual | Views + attribute limits | Manual |
| Runtime metrics | `NewGoCollector` | `contrib` runtime instrumentation | `WriteProcessMetrics` |
| License | Apache-2.0 | Apache-2.0 | Apache-2.0 |

The star counts are closer than the maturity gap suggests: OpenTelemetry Go has absorbed an enormous amount of work in two years, while `client_golang` has stayed deliberately small. That stability is a feature — its API has not broken for years.

## Decision Matrix: Match the Library to the Job

| Your situation | Recommended library | Why |
|---|---|---|
| Existing Prometheus + Grafana stack, no tracing yet | `prometheus/client_golang` | Zero-friction scrape, familiar `rate()` queries, huge bucket of examples |
| Traces and metrics must share resource attributes | OpenTelemetry Go | One SDK, one exporter, correlated `service.name` and trace IDs |
| Backend is VictoriaMetrics, extremely high event rate | `VictoriaMetrics/metrics` | Purpose-built for low-allocation counters and gauges |
| Multi-tenant SaaS where label blowups are a real risk | OpenTelemetry Go + Views | Per-instrument attribute filtering and aggregation control |
| Batch job shorter than the scrape interval | `VictoriaMetrics/metrics` push or OTel push | Push model avoids missed scrapes entirely |
| You need exemplars linking metrics to traces | `client_golang` or OTel | `VictoriaMetrics/metrics` cannot emit exemplars |

## prometheus/client_golang — The Default That Refuses to Break

This is the library that defined what "Go metrics" means. Registration is global, exposition is a handler, and the text format is what every scraper on earth understands.

```go
package main

import (
	"net/http"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

var (
	httpRequests = promauto.NewCounterVec(prometheus.CounterOpts{
		Namespace: "shop",
		Subsystem: "api",
		Name:      "http_requests_total",
		Help:      "Total HTTP requests by route and status.",
	}, []string{"route", "status"})

	requestDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Namespace: "shop",
		Subsystem: "api",
		Name:      "request_duration_seconds",
		Help:      "Request latency by route.",
		Buckets:   []float64{0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5},
	}, []string{"route"})
)

func instrument(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		timer := prometheus.NewTimer(requestDuration.WithLabelValues(r.URL.Path))
		defer timer.ObserveDuration()
		next.ServeHTTP(w, r)
		httpRequests.WithLabelValues(r.URL.Path, "200").Inc()
	})
}

func main() {
	http.Handle("/metrics", promhttp.Handler())
	http.ListenAndServe(":2112", nil)
}
```

**What it gets right:** the `promauto` helpers remove boilerplate, `prometheus.NewTimer` makes latency instrumentation a two-liner, and `promhttp.HandlerFor` lets you expose a custom registry without touching globals. Its `NewGoCollector` gives you goroutine counts, GC pauses and heap stats for free — the first thing you will actually look at during an incident.

**Where it bites:**

- **Duplicate registration panics in tests.** Register the same collector twice and you get a panic, not an error. Keep collectors in package-level vars or build a fresh registry per test with `prometheus.NewRegistry()`.
- **`promauto` hides failures.** It panics on invalid metric names at init time — good in production, annoying when a refactor renames a metric.
- **Cardinality is entirely your problem.** There is no per-instrument limit. One `user_id` label and you are the incident.
- **Classic histogram buckets are forever.** Changing buckets in a running deployment creates a second series set; plan bucket layout before you ship, not after.

If you scrape with a collector and forward via `prometheusremotewrite` or `otlphttp`, you already have a standards-compliant pipeline. That is the cheapest way to "adopt OTLP" without rewriting any code.

## OpenTelemetry Go — The Standard, With a Setup Tax

OpenTelemetry Go splits the API (`go.opentelemetry.io/otel/metric`) from the SDK (`go.opentelemetry.io/otel/sdk/metric`). That separation is what makes libraries instrumentable without dragging in an exporter, but it also means your `main()` grows.

```go
package main

import (
	"context"
	"log"
	"net/http"
	"time"

	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetrichttp"
	sdkmetric "go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/metric"
)

func newMeterProvider(ctx context.Context) (*sdkmetric.MeterProvider, error) {
	exp, err := otlpmetrichttp.New(ctx,
		otlpmetrichttp.WithEndpoint("otel-collector:4318"),
		otlpmetrichttp.WithInsecure(),
	)
	if err != nil {
		return nil, err
	}

	provider := sdkmetric.NewMeterProvider(
		sdkmetric.WithReader(sdkmetric.NewPeriodicReader(exp,
			sdkmetric.WithInterval(15*time.Second))),
	)
	return provider, nil
}

func main() {
	ctx := context.Background()
	provider, err := newMeterProvider(ctx)
	if err != nil {
		log.Fatal(err)
	}
	defer provider.Shutdown(ctx)

	meter := provider.Meter("shop/api")
	requests, _ := meter.Int64Counter("http.requests",
		metric.WithDescription("Total HTTP requests."),
		metric.WithUnit("{request}"))

	requests.Add(ctx, 1, metric.WithAttributes(
		attribute.String("route", "/cart"),
		attribute.String("status", "200"),
	))
}
```

**What it gets right:** one SDK for all three signals, resource attributes that survive into traces, and **Views** — the single best cardinality-control mechanism in this comparison. A View can drop an attribute, rename a metric, or swap a histogram for an explicit-bucket aggregation without touching call sites:

```go
view := sdkmetric.NewView(
	sdkmetric.Instrument{Name: "http.requests"},
	sdkmetric.Stream{
		Aggregation: sdkmetric.AggregationSum{},
		AttributeFilter: attribute.NewAllowKeysFilter("route", "status"),
	},
)
provider := sdkmetric.NewMeterProvider(
	sdkmetric.WithView(view),
	sdkmetric.WithReader(sdkmetric.NewPeriodicReader(exp)),
)
```

**Where it bites:**

- **More allocation per update.** Attribute sets are built and merged on the hot path. For counters incremented millions of times per second, this is measurable — and it is why the VictoriaMetrics library exists.
- **Configuration surface is large.** Readers, exporters, views, resource detection, shutdown ordering. Getting `Shutdown` wrong loses the final export.
- **Not scrape-native.** If your Prometheus server scrapes `/metrics`, you need `prometheus.New` from `go.opentelemetry.io/otel/exporters/prometheus` and a `promhttp` handler — extra moving parts for the same result.

If you already run a collector, OTel Go is the least opinionated long-term bet: the collector absorbs backend churn, and the SDK stays vendor-neutral.

## VictoriaMetrics/metrics — The Hot-Path Specialist

VictoriaMetrics/metrics (often imported as `vmmetrics`) drops the registry abstraction almost entirely. Metrics are addressed by their final name and labels, which is fast and slightly alarming the first time you see it.

```go
package main

import (
	"net/http"

	"github.com/VictoriaMetrics/metrics"
)

var (
	requests = metrics.NewCounter(`vm_http_requests_total{route="/cart",status="200"}`)
	queueLen = metrics.NewGauge(`vm_queue_depth{queue="orders"}`, nil)
)

func init() {
	metrics.GetOrCreateGauge(`vm_inflight_requests`, nil)
	queueLen.Set(0)
}

func main() {
	requests.Inc()
	queueLen.Set(42)

	http.HandleFunc("/metrics", func(w http.ResponseWriter, r *http.Request) {
		metrics.WritePrometheus(w, true) // true: expose process metrics too
	})
	http.ListenAndServe(":8428", nil)
}
```

**What it gets right:** near-zero allocation counters, `GetOrCreate*` families for dynamic label sets, built-in process metrics, and a push mode (`metrics.InitPush`) that solves the short-lived-job problem without a Pushgateway. For a proxy or a queue consumer doing 100k operations per second, the difference in GC pressure is the whole point.

**Where it bites:**

- **No classic Prometheus histograms.** `metrics.NewHistogram` produces VictoriaMetrics `vmrange` buckets. If a downstream consumer expects `le`-labelled buckets, your `histogram_quantile` queries will silently return nothing.
- **No exemplars.** Trace-to-metric correlation is not available.
- **Metric names are strings at the call site.** Typos become new series instead of compile errors. Wrap them in constants.
- **Ecosystem gravity.** Dashboards, alerts and recording rules written against `client_golang` conventions need review, because Go runtime metrics arrive under different names.

## Migration Playbook That Does Not Cause an Outage

Teams usually arrive here mid-migration. The safe sequence:

1. **Keep exposition stable.** Whatever SDK you use, keep `/metrics` serving Prometheus text until every dashboard is migrated. The collector can scrape and re-export to any backend.
2. **Move instrument by instrument, not service by service.** Metric names are the contract; a partial migration with duplicated names creates double-counting. Rename during migration, then delete the old instrument.
3. **Bridge before you rewrite.** `client_golang` + OTel Collector (`prometheusreceiver` → `otlphttp`) gives you OTLP with zero application changes. Do this first, measure, then decide whether the SDK migration is worth it.
4. **Set cardinality limits before you need them.** In OTel, use Views with allow-key filters. In `client_golang`, add a CI check that greps for high-cardinality label names (`user_id`, `request_id`, `email`, `session_id`) in metric definitions.
5. **Re-baseline your alerts.** Histogram semantics differ across all three libraries. Recompute p99 thresholds from real traffic after the switch — do not carry over tuned thresholds blindly.

## Common Pitfalls (Learned the Expensive Way)

- **Route labels from raw URL paths.** `/orders/8123` and `/orders/8124` are two series. Always label by route template, never by resolved path.
- **Timer without defer.** `prometheus.NewTimer(...).ObserveDuration()` called only on success means your latency histogram under-reports errors exactly when it matters.
- **One shared histogram for all routes.** Bucket layout that fits a 2ms cache hit will not resolve a 3-second report job. Split by route class or use native histograms.
- **Gauge callbacks that panic.** `metrics.NewGauge(name, f)` and Prometheus `GaugeFunc` execute on scrape. A nil pointer there breaks the entire scrape, not just one metric.
- **Forgetting `Shutdown` in OTel.** The periodic reader buffers up to one interval. `os.Exit` skips the final flush; call `provider.Shutdown(ctx)` in your shutdown path.
- **Testing against the global registry.** Use a dedicated `prometheus.NewRegistry()` per test, and `testutil.ToFloat64` / `testutil.CollectAndCount` to assert values instead of parsing text output.

For the collector-side view of this stack, see our [Kubernetes monitoring operators comparison](../2026-04-30-k8s-monitoring-operators-kube-prometheus-victoriametrics-opentelemetry-guide/) and the [metric relay guide](../2026-04-29-promxy-vs-victoriametrics-vmagent-vs-grafana-mimir-self-hosted-metric-relay-guide-2026/). If you are still choosing a test stack for the code that emits these metrics, our [Go testing frameworks comparison](../2026-07-22-go-testing-frameworks-testify-goconvey-ginkgo/) covers that ground.
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Go Metrics in 2026: prometheus/client_golang vs OpenTelemetry Go vs VictoriaMetrics/metrics",
  "description": "A hands-on comparison of the three Go metrics libraries that matter in 2026: instrumentation API, cardinality control, histogram cost, and migration paths.",
  "datePublished": "2026-10-24",
  "dateModified": "2026-10-24",
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

## FAQ

**Which Go metrics library should a new project use in 2026?**
If you only run Prometheus, use `prometheus/client_golang` — least code, most examples. If you plan to adopt tracing or export to a vendor backend, start with OpenTelemetry Go so you never have to migrate later.

**Does OpenTelemetry Go replace prometheus/client_golang?**
Not at the wire level. OTel can expose a Prometheus endpoint through its Prometheus exporter, and Prometheus can scrape any OTLP-speaking collector. They coexist; the choice is about SDK ergonomics, not protocol incompatibility.

**How much faster is VictoriaMetrics/metrics than client_golang?**
On counter-heavy hot paths the gap is real and mostly shows up as reduced garbage collection pressure, because it avoids per-update label map allocation. The difference is irrelevant for services doing a few thousand operations per second and significant for proxies or queue workers at six figures per second.

**Can I use two libraries in one service?**
Yes, but keep them on separate registries and separate metric prefixes. Two libraries writing the same metric name into the same exposition endpoint produces duplicate series and confusing query results.

**What is the cheapest way to reduce metric cardinality today?**
Audit label values, not label counts. A metric with one label is dangerous if that label has unbounded values. Drop the offending label, aggregate the remainder, and add a CI check so it does not come back.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)


