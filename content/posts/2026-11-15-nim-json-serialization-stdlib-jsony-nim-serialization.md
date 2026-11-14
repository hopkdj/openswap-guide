---
title: "Nim JSON in 2026: std/json vs jsony vs nim-serialization — 5x Faster or Just Different?"
date: "2026-11-15"
description: "A benchmark-backed comparison of Nim's three JSON stacks: the standard library's JsonNode DOM, jsony's direct-to-object parser and nim-serialization's schema-first framework."
tags: ["nim", "json", "serialization", "performance"]
cover: "/img/screenshots/nim-json-serialization.jpg"
draft: false
---

jsony's own README contains a table that should make any Nim developer stop and read it twice: serializing the same payload takes **1.37 ms** with jsony and **8.51 ms** with the standard library. Deserializing is worse — **4.20 ms** versus **14.47 ms**. That is not a rounding difference. On a service that parses a few thousand requests per second, it is the difference between a comfortable CPU graph and a permanently pegged core.

But raw speed is only one axis, and picking a JSON library on microseconds alone is how people end up hand-rolling fragile parsing code. The three stacks that matter in Nim in 2026 solve different problems: `std/json` gives you a dynamic document tree, `jsony` gives you direct object mapping with hooks, and `nim-serialization` gives you a schema-first framework with strict standards compliance.

**TL;DR:** Use **jsony** for hot paths and plain object mapping — it is roughly 3–6x faster than the standard library and needs one `nimble install`. Use **std/json** for config files, dynamic JSON you must inspect, and anything you want zero dependencies for. Use **nim-serialization** when you need RFC 8259 compliance, multiple formats (JSON, TOML, Protobuf, SSZ) behind one API, or compile-time decoding.

## The Contenders at a Glance

| | **std/json** | **jsony** | **nim-serialization** |
|---|---|---|---|
| **Repository** | `nim-lang/Nim` | `treeform/jsony` | `status-im/nim-serialization` |
| **Stars** | 18,310 (compiler) | 300 | 77 |
| **Last push** | 2026-11-14 | 2026-10-28 | 2026-10-18 |
| **Model** | Parse to `JsonNode` DOM, then `to()` | Parse directly into your object | Reader/Writer per format, typed codecs |
| **Dependencies** | None (stdlib) | None beyond stdlib | `serialization` + `json_serialization`, `faststreams` |
| **Install** | ships with Nim | `nimble install jsony` | `nimble install json_serialization` |
| **Unknown JSON fields** | Rejected by `to()` unless handled | Ignored | Configurable via flavors |
| **Missing fields** | Error | Keeps the object's default value | Error unless defaulted |
| **snake_case → camelCase** | Manual | Automatic | Via `{.serializedFieldName.}` / flavors |
| **Formats beyond JSON** | No | No | TOML, Protobuf, SSZ behind the same API |
| **RFC 8259 compliance** | Practical, not exhaustive | Loose by design | Full, passes JSONTestSuite |
| **Serialize (min / avg)** | 8.222 / 8.510 ms | **1.317 / 1.365 ms** | 2.043 / 3.448 ms |
| **Deserialize (min / avg)** | 14.326 / 14.473 ms | **4.134 / 4.196 ms** | 7.119 / 14.276 ms |

The benchmark numbers are the ones published in jsony's README, measured by its author on the same payload for all four libraries. Treat them as directional — they are reproducible with the repo's own benchmark suite, and the ranking has been stable across releases, but your payload shape and your compiler flags will move the absolute values.

## Decision Matrix: Pick by Use Case

| Your situation | Pick | Why |
|---|---|---|
| HTTP service parsing request bodies at volume | **jsony** | Direct-to-object parsing skips the DOM allocation entirely |
| Reading a config file at startup | **std/json** | Zero dependencies, and you want to inspect values dynamically |
| Arbitrary third-party JSON with unknown shape | **std/json** | `JsonNode` lets you walk and validate before converting |
| Strict spec compliance / hostile input | **nim-serialization** | Passes JSONTestSuite, configurable parse limits |
| Same types over JSON, TOML and Protobuf | **nim-serialization** | One API, four format backends |
| Compile-time constants decoded from JSON | **nim-serialization** | `decode` works in `const` and `static` blocks since v0.4.4 |
| Mapping REST payloads with `snake_case` keys | **jsony** | Handles the naming conversion automatically |
| Library code you cannot add dependencies to | **std/json** | It is in the compiler distribution |

## std/json: The DOM You Already Have

The standard library's model is two-step: parse the text into a `JsonNode` tree, then convert the tree into your type. It is always available, it is well documented, and for anything that is not a hot path it is entirely adequate.

```nim
import std/json

let node = parseJson("""{"name": "Ada", "tags": ["math", "engines"], "age": 36}""")

echo node["name"].getStr()          # Ada
echo node["tags"][0].getStr()       # math
echo node["age"].getInt()           # 36

# Building JSON without a schema
let payload = %*{
  "name": "Ada",
  "active": true,
  "scores": [98, 91, 87]
}
echo $payload
```

Converting to a typed object uses the `to` macro:

```nim
import std/json

type User = object
  name: string
  age: int

let raw = """{"name": "Ada", "age": 36}"""
let user = raw.parseJson().to(User)
echo user.name, " is ", user.age
```

The trade-off is visible in the type system: every value passed through `JsonNode` is heap-allocated, every field lookup is a hash lookup by string, and the intermediate tree becomes garbage the moment `to()` finishes. That is exactly what jsony's benchmark is measuring. The second cost is strictness — `to()` expects the JSON keys to line up with your object's fields, so a payload that renames `user_name` to `userName` needs manual mapping or a custom `%`/`to` hook.

Where `std/json` still wins without argument: scripts that read a config file, tools that must accept arbitrary JSON and report on its structure, and any code inside a project that refuses third-party dependencies. Nim ships it, so it is the only option with a guaranteed zero-install path.

## jsony: Direct-to-Object Parsing With Hooks

jsony's premise is stated bluntly in its README: "Real world json is never what you want." Extra fields, missing fields, `camelCase` versus `snake_case`, inconsistent naming — the library's job is to absorb that mess and hand you an object.

Install and use:

```bash
nimble install jsony
```

```nim
import jsony

type Entry = object
  name: string
  colorBlend: string       # matches "color_blend" automatically
  retries: int             # missing in JSON -> keeps default 0

let raw = """{"name": "Ada", "color_blend": "red", "extra": "ignored"}"""
let entry = raw.fromJson(Entry)

echo entry.name        # Ada
echo entry.colorBlend  # red
echo entry.retries     # 0

echo entry.toJson()    # {"name":"Ada","colorBlend":"red","retries":0}
```

The documented type coverage is broad: numbers and strings, `seq` and arrays, objects and ref objects, `Option`, enums, tuples, characters, `HashTable` and `OrderedTable`, `HashSet` and `OrderedSet`, and `JsonNode` itself for mixed payloads. When a type needs custom logic, `parseHook` lets you take over parsing for it — that is the escape hatch for dates, decimals or tagged unions.

The performance claim is architectural rather than magical. As the README explains, the standard library "first parses or serializes json into JsonNodes and then turns the JsonNodes into your objects with the `to()` macro". jsony skips the intermediate tree, avoids `StringStream` dispatch overhead by reading and writing memory buffers directly, and parses numbers from the buffer without allocating an intermediate string. Fewer allocations means less GC pressure, which is why the win grows with payload size.

The published benchmark, run x100 on the same data:

```
Serialize (min / avg, ms)
treeform/jsony ..................... 1.317 / 1.365
status-im/nim-json-serialization ... 2.043 / 3.448
planetis-m/eminim .................. 5.951 / 9.305
disruptek/jason .................... 6.858 / 7.043
nim std/json ....................... 8.222 / 8.510

Deserialize (min / avg, ms)
treeform/jsony ..................... 4.134 / 4.196
status-im/nim-json-serialization ... 7.119 / 14.276
planetis-m/eminim .................. 7.761 / 8.001
nim std/json ...................... 14.326 / 14.473
```

Note the variance column in the original table: `nim-serialization`'s deserialize average is double its minimum, which suggests occasional allocation spikes. jsony's numbers are tight, which is what you want for latency predictability.

The cost of the loose philosophy is that jsony will not tell you when a payload is wrong. Missing fields silently become defaults; a `null` where you expected a string may become an empty string or raise, depending on the type. If your service must reject malformed input with a specific error, you are adding validation on top rather than getting it from the parser.

## nim-serialization: Schema-First, Standards-Compliant, Multi-Format

`nim-serialization` inverts the design. Instead of a parser with a fixed behaviour, it defines a common interface — a `Reader` and `Writer` per format — and then ships format packages on top: `json_serialization`, `toml_serialization`, `protobuf_serialization`, `ssz_serialization`.

```nim
import json_serialization

type Request = object
  jsonrpc: string
  `method`: string

let
  json = """{"jsonrpc": "2.0", "method": "name"}"""
  decoded = Json.decode(json, Request)

echo decoded.jsonrpc
echo Json.encode(decoded, pretty = true)
```

Beyond the happy path, its feature list is the most complete of the three:

- **Full RFC 8259 compliance**, including the genuinely awkward corners of JSON number handling, and it passes the JSONTestSuite conformance corpus.
- **Configurable parsing limits** and well-defined handling of malformed or malicious input, backed by fuzzing plus manual test coverage.
- **Flavors** — multiple serialization styles per Nim type, so one type can be encoded differently for an internal API and a public one.
- **Partial parsing** — efficient skipping of tags and values you do not need.
- **Interoperability with `std/json`** — `JsonValueRef` for DOM-style access and `JsonString` for passing nested documents between layers.
- **Compile-time encode/decode** since v0.4.4, so a `const` value can be initialised from JSON.

The extra machinery costs something: two packages (`serialization` plus the format package), a `faststreams` dependency, and a learning curve around flavors and field annotations. The README is honest about maturity as well — the project labels its stability as experimental, which is a fair description of an API that has evolved across versions.

Where it is clearly the right answer: anything that must accept untrusted JSON and report precise errors, codebases that serialise to more than one format, and teams that want the same type annotations to drive JSON, TOML and Protobuf without three sets of converters.

## Reading the Benchmarks Honestly

Three cautions before you rewrite anything based on the table above.

**Compile with `-d:release` (or `-d:danger`).** Nim's default debug build disables optimisations and adds runtime checks; a benchmark run in debug mode measures the wrong thing. jsony's numbers come from a release build of the benchmark suite.

**Payload shape decides the gap.** jsony's advantage comes from skipping the DOM, so it grows with the number of objects and fields. If you parse one small config object at startup, the difference between 1.3 ms and 8.5 ms per hundred iterations is invisible. If you parse 50 KB request bodies at 2,000 requests per second, it is the difference between 3% and 45% of a core.

**Compare end-to-end, not micro.** The parser is rarely the whole cost — HTTP framing, TLS, database round-trips and JSON encoding of the response usually dominate. Benchmark your endpoint, not a standalone `parseJson` loop. For that, the same `wrk -t4 -c100 -d30s` approach from our [Nim async I/O comparison](../2026-10-29-nim-async-io-chronos-asyncdispatch-threadpool/) gives you a latency distribution rather than a single throughput number.

What the numbers do reliably tell you is the *cost structure*: `std/json` allocates an intermediate tree per document, `nim-serialization` streams into objects with more validation work, and `jsony` writes straight into fields. That ordering holds regardless of machine.

## Migration Notes and Pitfalls

- **Do not mix `JsonNode` and typed parsing in one hot path.** A common pattern is `parseJson` for validation followed by `.to()` — that is the slowest of all worlds, because you pay for the DOM and then throw it away.
- **Missing fields behave differently, and this is the bug you will actually ship.** jsony keeps defaults; `std/json`'s `to()` and `nim-serialization` error. If your type has `count: int` and the upstream omits it, jsony gives you `0` silently.
- **Number precision needs a decision.** Large integers and decimals do not round-trip identically across all three. If you handle money or identifiers above 2^53, use string encoding or a decimal type at the boundary.
- **`Option[T]` is the honest representation of a nullable field.** In jsony, `Option` maps to `null` cleanly; a plain `string` will not distinguish "absent" from "empty".
- **Compile-time decoding has limits.** `nim-serialization` supports it since v0.4.4, but only for constants the compiler can evaluate — no file I/O, no environment lookups.
- **Do not benchmark without disabling GC effects deliberately.** If you are comparing libraries, run each in a fresh process and report both min and average; the spread is often more informative than the mean.
- **`jsony`'s automatic `snake_case` conversion can collide.** Two JSON keys that differ only in separator style (`user_name` and `userName`) map to the same field. Validate upstream if that is possible in your data.

## Which Should You Actually Use?

**For a service, use jsony.** It is the pragmatic default: one dependency, an API that fits in your head, automatic name conversion, and a 3–6x advantage over the standard library on exactly the workload services have. The looseness is a real risk, so pair it with schema validation at the edge — a generated validator or an explicit check after `fromJson` — rather than relying on the parser to reject bad input.

**For scripts and tools, keep std/json.** Nobody wants a dependency for reading `config.json`, and `JsonNode` is the right structure when you genuinely do not know the shape ahead of time. The performance penalty is irrelevant at startup scale.

**For protocol work or multi-format serialisation, use nim-serialization.** RFC 8259 compliance, JSONTestSuite coverage, configurable parse limits and a format-agnostic interface are things you cannot bolt onto a loose parser later. If you are implementing a wire protocol or handling untrusted input at a boundary, that is the trade you want.

The combination I would ship in 2026: **jsony on request paths, std/json for configuration and diagnostics, nim-serialization wherever the input is hostile or the output must be standards-exact.** The three coexist without conflict because they operate on different layers — and in a Nim project, the compiler will tell you immediately if you have mixed up the types.

For more on the surrounding stack, see our [Nim web frameworks comparison](../2026-07-25-nim-web-frameworks-jester-prologue-httpbeast-mofuw/) to pick the server this parsing runs behind, our [Nim toolchain guide](../2026-10-25-nim-toolchain-nimble-choosenim-atlas-comparison/) for pinning compiler and package versions reproducibly, and our [async I/O comparison](../2026-10-29-nim-async-io-chronos-asyncdispatch-threadpool/) if your JSON parsing competes with the event loop for CPU.

## FAQ

### Is jsony really faster than std/json?

Yes, on the workload jsony's own benchmark measures: roughly 6x faster serialisation and 3.4x faster deserialisation on the same payload. The gain comes from parsing directly into objects and avoiding the intermediate `JsonNode` tree and `StringStream` dispatch. Measure your own payload with `-d:release` before assuming the ratio transfers.

### Does jsony handle snake_case JSON keys?

Yes. The library converts `snake_case` keys to Nim's `camelCase` field names automatically, which is why a field declared as `colorBlend` matches `"color_blend"` in the document. Fields that are missing in the JSON keep the object's default value.

### What happens to extra JSON fields with std/json?

`std/json`'s `to()` macro maps JSON keys onto object fields and expects the shape to match — a field that is missing from the document is an error, and a document that carries additional keys needs to be handled before conversion. jsony ignores unknown keys by design; `nim-serialization` makes strictness configurable through flavors.

### Can I use nim-serialization with TOML or Protobuf?

Yes. `nim-serialization` defines the common interface, and format packages sit on top: `json_serialization`, `toml_serialization`, `protobuf_serialization` and `ssz_serialization`. The same type annotations drive all of them, which is the main reason to accept its extra dependency weight.

### Is nim-serialization production-ready?

Its README labels the project's stability as experimental, and the API has changed across versions. That said, it passes JSONTestSuite for RFC 8259 compliance and has fuzzing plus test coverage for malformed input, which is more than most JSON libraries offer. Pin the version in your `.nimble` file and read the changelog before upgrading.

### Why is my benchmark slower than the numbers here?

Almost always because the build was not a release build. Nim's debug mode keeps runtime checks and disables optimisations, so both libraries look far slower and the ratio between them changes. Compile with `-d:release`, run each library in a fresh process, and report min as well as average.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Nim JSON in 2026: std/json vs jsony vs nim-serialization",
  "description": "Benchmark-backed comparison of Nim JSON libraries: the stdlib JsonNode DOM, jsony direct-to-object parsing and nim-serialization schema-first codecs.",
  "datePublished": "2026-11-15",
  "dateModified": "2026-11-15",
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
