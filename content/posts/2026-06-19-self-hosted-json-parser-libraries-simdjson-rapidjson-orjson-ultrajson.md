---
title: "Self-Hosted JSON Parser Libraries: simdjson vs rapidjson vs orjson vs UltraJSON"
date: "2026-06-19"
tags: ["json", "serialization", "performance", "developer-tools", "comparison", "self-hosted", "guide", "c-plus-plus", "python"]
draft: false
---

## Introduction

JSON (JavaScript Object Notation) is the backbone of modern web applications, APIs, and configuration files. Every self-hosted service you deploy — whether it is an API gateway, a monitoring dashboard, or a message queue — processes JSON somewhere in its pipeline. The choice of JSON parsing library directly impacts throughput, latency, and CPU utilization of your entire stack.

Most developers use their programming language's built-in JSON parser and never think twice. However, for performance-critical self-hosted services handling millions of requests per day, the difference between a standard library parser and a specialized high-performance parser can be dramatic — sometimes 5x to 20x faster.

In this guide, we compare four battle-tested JSON parsing libraries that power some of the largest self-hosted systems in production: **simdjson** (used by ClickHouse, Node.js, and Apache Doris), **rapidjson** (used by Tencent and countless C++ projects), **orjson** (the go-to choice for Python FastAPI and data engineering pipelines), and **UltraJSON** (the original fast Python JSON library).

## Why JSON Parser Performance Matters for Self-Hosted Services

When you run a self-hosted API gateway like Kong or APISIX, every incoming request body needs to be parsed as JSON. When your monitoring stack ingests millions of log lines per day, each one is a JSON document. When your database exports query results, JSON serialization is on the critical path.

A slow JSON parser acts as a hidden bottleneck. You might scale horizontally, add more replicas, and increase CPU allocation — when the real fix is a faster parsing library that reduces per-request overhead by 80%. In self-hosted environments where resources are finite, optimizing at the library level yields compounding returns across the entire stack.

## Comparison Table

| Feature | simdjson | rapidjson | orjson | UltraJSON |
|---------|----------|-----------|--------|-----------|
| Language | C++ | C++ (header-only) | Python (Rust core) | C (Python bindings) |
| Stars | 23,867 | 15,096 | 8,117 | 4,485 |
| License | Apache 2.0 | MIT-like | Apache 2.0 | BSD |
| API Style | DOM, On-Demand | DOM, SAX | Python native | Python native |
| SIMD Acceleration | Yes (AVX2, NEON) | No | Yes (via Rust) | No |
| Standard Compliance | Strict RFC 8259 | RFC-compatible | Strict RFC 8259 | Lenient by default |
| Largest User | ClickHouse, Node.js | Tencent, Unity | FastAPI, Pandas | Various Python apps |
| Peak Throughput | ~2.4 GB/s | ~300 MB/s | ~800 MB/s | ~200 MB/s |
| Updated | 2026-06-15 | 2025-02-05 | 2026-06-04 | 2026-06-14 |

## simdjson: Parsing Gigabytes per Second

[simdjson](https://github.com/simdjson/simdjson) is the undisputed performance champion, achieving parsing speeds of over 2 gigabytes per second on modern hardware. Developed by Daniel Lemire and collaborators, it was the first JSON parser to leverage SIMD (Single Instruction Multiple Data) instructions — specifically AVX2 on x86 and NEON on ARM — to process 64 bytes of JSON at a time.

simdjson offers two parsing modes: **DOM** (Document Object Model), which parses the entire document into a tree structure, and **On-Demand**, a lazy parsing API that only processes the fields you access. The On-Demand mode further reduces memory allocation and improves performance for selective field extraction.

```cpp
#include "simdjson.h"

simdjson::ondemand::parser parser;
auto json = R"({"name": "nginx", "version": "1.25.3", "connections": 15234})"_padded;
simdjson::ondemand::document doc = parser.iterate(json);
std::string_view name = doc["name"];
int64_t connections = doc["connections"];
```

simdjson is used in production by Facebook's Velox query engine, ClickHouse's JSON column type, the Node.js runtime itself, WatermelonDB for mobile, Apache Doris, Milvus vector database, and StarRocks. If your self-hosted stack includes any of these tools, you are already benefiting from simdjson.

**Best for:** Performance-critical C++ services where JSON throughput is a bottleneck, especially analytics databases, query engines, and high-throughput API gateways.

## rapidjson: The Battle-Tested Workhorse

[rapidjson](https://github.com/Tencent/rapidjson) is a header-only C++ library developed at Tencent. Despite not using SIMD acceleration, it achieves impressive performance through careful memory management and zero-copy string handling. Its header-only design means no build system changes — just include the header files.

rapidjson offers both **DOM** (full tree parsing) and **SAX** (streaming event-based) APIs, giving developers flexibility to choose between convenience and raw speed. It supports full RFC-compatible JSON with UTF-8 validation, and handles edge cases like duplicate keys, integer overflow, and deeply nested structures.

```cpp
#include "rapidjson/document.h"

const char* json = R"({"server": "apache", "requests_per_sec": 8421})";
rapidjson::Document doc;
doc.Parse(json);
const char* server = doc["server"].GetString();
int rps = doc["requests_per_sec"].GetInt();
```

rapidjson's stability and maturity (created in 2014) make it a safe choice for long-running self-hosted services. It is used in Tencent's backend infrastructure, Unity game engine, and numerous embedded systems where predictable performance matters more than peak throughput.

**Best for:** C++ projects that prioritize stability, header-only integration, and predictable performance over absolute maximum throughput.

## orjson: The Python Speed Demon

[orjson](https://github.com/ijl/orjson) is a Python JSON library with a Rust core that dramatically outperforms the standard library's `json` module. It is the default JSON serializer for FastAPI, the most popular Python web framework, and is widely used in data engineering pipelines, ETL tools, and API servers.

orjson's key advantage is native support for Python data types that the standard library struggles with: `dataclasses`, `datetime` objects, `numpy` arrays, `UUID`, and `Decimal`. It serializes these types correctly without requiring custom encoders, and does so significantly faster.

```python
import orjson, datetime, numpy as np

data = {
    "service": "prometheus",
    "timestamp": datetime.datetime.now(),
    "metrics": np.array([1.2, 3.4, 5.6])
}
# Serialize to bytes (not str — orjson outputs bytes for speed)
result = orjson.dumps(data)
# Deserialize
parsed = orjson.loads(result)
```

Compared to the standard `json` module, orjson is typically 3-5x faster for serialization and 2-3x faster for deserialization on real-world API payloads. It also produces smaller output (no unnecessary whitespace) and handles Unicode correctly by default.

**Best for:** Python self-hosted services where JSON serialization is on the hot path — FastAPI applications, data ingestion pipelines, metrics exporters, and any service that processes thousands of JSON documents per second.

## UltraJSON: The Original Fast Python JSON

[UltraJSON](https://github.com/ultrajson/ultrajson), or ujson, pioneered fast JSON parsing in Python. Written in C with Python bindings, it was the default "fast JSON" choice for over a decade before orjson emerged. It remains widely deployed and battle-tested.

UltraJSON's approach is simpler than orjson: a pure C implementation tightly bound to Python's object model. It excels at parsing large arrays of numbers and simple data structures, though it is more lenient with edge cases (accepting slightly non-standard JSON by default). It does not natively handle dataclasses or numpy types without custom encoders.

```python
import ujson

data = {"endpoint": "/api/metrics", "status_codes": [200, 301, 404, 503]}
# ujson works as a drop-in replacement for the standard json module
encoded = ujson.dumps(data)
decoded = ujson.loads(encoded)
```

For projects already using ujson, the migration path to orjson is straightforward but may require updating custom encoder logic. UltraJSON remains a solid choice for projects that need faster JSON but want minimal code changes from the standard library.

**Best for:** Legacy Python projects already using ujson, or simple JSON workloads where the complexity of orjson's type handling is unnecessary.

## Choosing the Right JSON Parser for Your Self-Hosted Stack

The choice depends on your language ecosystem and performance requirements:

- **C++ services with extreme throughput requirements**: Use simdjson for its SIMD-accelerated parsing. Your analytics database, log processor, or API gateway will see immediate CPU savings.
- **C++ services prioritizing stability**: Use rapidjson for its header-only simplicity and decade-long track record in production.
- **Python API servers and data pipelines**: Use orjson as the default. FastAPI already does this, and migrating from the standard library is a one-line change in most cases.
- **Simple Python workloads**: UltraJSON remains a viable drop-in replacement with proven reliability.

For self-hosted environments, the CPU savings from switching to a faster JSON parser can reduce infrastructure costs by 15-30% on JSON-heavy workloads — a meaningful improvement for home lab and small business deployments.

For related reading, see our [Protobuf tools guide](../2026-05-07-self-hosted-protobuf-tools-buf-protolock-protovalidate-guide/) for binary serialization alternatives, and our [API gateway comparison](../self-hosted-api-gateway-apisix-kong-tyk-guide/) where JSON parsing is on the critical request path.

## FAQ

### Do I need a specialized JSON parser for my self-hosted services?

If your service handles fewer than 10,000 JSON documents per second, the standard library parser in your language is likely sufficient. The specialized parsers covered here become valuable when JSON processing accounts for more than 5% of your CPU time, or when you are optimizing a performance-critical path like API request handling or database import/export.

### Is simdjson compatible with ARM-based servers?

Yes. simdjson supports ARM NEON SIMD instructions, which are available on all modern ARM64 processors including AWS Graviton, Ampere Altra, and Raspberry Pi 5. Performance on ARM is slightly lower than x86 AVX2 but still substantially faster than non-SIMD parsers.

### Can I use orjson as a drop-in replacement for Python's json module?

Orjson is nearly a drop-in replacement. The main differences are that `orjson.dumps()` returns `bytes` instead of `str`, and it rejects non-standard JSON (e.g., `NaN`, `Infinity`) unless explicitly allowed. For most API applications, switching is as simple as replacing `import json` with `import orjson as json`.

### How does rapidjson handle Unicode and non-ASCII characters?

rapidjson fully supports UTF-8, UTF-16, and UTF-32 encodings with automatic transcoding. It validates all Unicode sequences and handles surrogate pairs correctly. For JSON containing Chinese, Japanese, or other non-Latin characters, rapidjson performs correct encoding without performance degradation.

### Which parser produces the smallest serialized JSON output?

orjson produces the most compact output by default (no unnecessary whitespace, sorted keys). simdjson and rapidjson both produce compact output in their default modes. UltraJSON's output size is comparable to the standard Python json module. For bandwidth-sensitive deployments, orjson's compact output can reduce API response sizes by 5-10%.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted JSON Parser Libraries: simdjson vs rapidjson vs orjson vs UltraJSON",
  "description": "Compare high-performance JSON parsing libraries for self-hosted services: simdjson (SIMD-accelerated), rapidjson (header-only C++), orjson (Rust-backed Python), and UltraJSON (C Python bindings). Benchmarks, code examples, and selection guide.",
  "datePublished": "2026-06-19",
  "dateModified": "2026-06-19",
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
