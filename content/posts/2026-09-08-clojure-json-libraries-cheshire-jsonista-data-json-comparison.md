---
title: "Clojure JSON Libraries in 2026: Cheshire vs jsonista vs data.json"
date: "2026-09-08"
tags: ["clojure", "json", "serialization", "jvm", "developer-tools"]
draft: false
---

Every Clojure service ends up parsing or emitting JSON, and every Clojure developer eventually asks the same question: **cheshire, jsonista, or data.json?** The three libraries look interchangeable at first glance — they all turn Clojure data into JSON strings and back — but they encode three genuinely different philosophies. Cheshire (1,558 stars, MIT) is the feature-rich Jackson wrapper that powers much of the ecosystem. jsonista (471 stars, EPL-2.0) is Metosin's explicit, benchmark-driven Jackson layer built for hot web request paths. data.json (578 stars, EPL-1.0, from the clojure org) is the zero-dependency, spec-compliant minimalists' choice. Picking wrong means living with surprise string keys, unparseable dates, or a classpath full of duplicated Jackson versions.

## TL;DR / Quick Verdict

If you serve JSON on a hot API route and control your stack (Reitit, Ring, Muuntaja), pick **jsonista** — it benchmarks roughly **2x faster than Cheshire on small payloads** and its explicit `object-mapper` design eliminates configuration guesswork. If you need pragmatic batteries-included behavior — automatic `Date`, `UUID`, `Set`, and custom-encoder support, plus SMILE binary JSON — pick **Cheshire**, the default in Babashka and the safest general-purpose choice. If you want a **zero-dependency** library that follows the JSON spec strictly and you are happy to write a `:key-fn` and `:value-fn` yourself, pick **data.json**. All three are stable, actively maintained open-source libraries; none of them will strand you.

## The Comparison Table

| Feature | Cheshire | jsonista | data.json |
|---|---|---|---|
| Repository | dakrone/cheshire | metosin/jsonista | clojure/data.json |
| GitHub stars (2026-09-08) | **1,558** | 471 | 578 |
| License | MIT | EPL-2.0 | EPL-1.0 |
| Latest release | 6.2.0 (Jackson 2.21.1) | current on Clojars | 2.5.2 |
| Last push | 2026-07-25 | 2026-08-31 | 2026-01-02 |
| External dependencies | Jackson (databind) | Jackson (databind) | **None** |
| Default decode key type | String (opt-in keywords) | String (opt-in keywords) | String (opt-in keywords) |
| Auto `Date`/`UUID`/`Set`/`Symbol` encoding | **Yes** | Via modules | Via `:value-fn` |
| Custom encoders/decoders | `add-encoder` (global) | Per-mapper `object-mapper` | `:key-fn` / `:value-fn` |
| SMILE (binary JSON) | **Yes** | No | No |
| Streaming / lazy parse | `parsed-seq` | Docs (`docs/streaming.md`) | `json/read` on Reader |
| Babashka built-in | **Yes** | No | No |
| Relative throughput (encode, 10-byte payload) | ~1.0x baseline | **~2.0x** | Slowest |
| Versioning | SemVer-ish | SemVer-ish | Explicitly non-semver ("endeavors to be non-breaking") |

## Decision Matrix

| Use case | Recommended library | Why |
|---|---|---|
| Ring/Reitit web API with JSON body parsing on every request | **jsonista** | Fastest encode/decode; explicit `keyword-keys-object-mapper` matches Ring conventions |
| General app logging, file export, mixed data with dates and UUIDs | **Cheshire** | Rich type support and custom encoders out of the box; forgiving API |
| CLI scripts, Babashka tasks, teaching material | **Cheshire** (in Babashka) or **data.json** | Babashka ships Cheshire built-in; data.json has zero deps for plain JVM scripts |
| A library that must not drag Jackson onto consumers' classpaths | **data.json** | Only one of the three with no external dependencies |
| Binary payloads alongside JSON | **Cheshire** | SMILE encode/decode via the same API |

## data.json: The Zero-Dependency Reference

data.json lives in the clojure org and states its goals with refreshing bluntness: *"JSON parser/generator to/from Clojure data structures. Key goals: compliant with JSON spec per json.org, no external dependencies."* There is no Jackson, no object mapper, no code generation — just functions over Clojure data. The core API is two functions plus their streaming siblings:

```clojure
(ns example
  (:require [clojure.data.json :as json]))

(json/write-str {:a 1 :b 2})
;;=> "{\"a\":1,\"b\":2}"

(json/read-str "{\"a\":1,\"b\":2}")
;;=> {"a" 1, "b" 2}     ;; <-- STRING keys by default

(json/read-str "{\"a\":1,\"b\":2}"
               :key-fn keyword)
;;=> {:a 1, :b 2}

(json/write-str {:a 1 :b 2}
                :key-fn #(.toUpperCase %))
;;=> "{\"A\":1,\"B\":2}"
```

The README is explicit that conversion is **not symmetric**: writing Clojure data to JSON is lossy, because JSON has fewer types than Clojure. Custom value handling goes through `:value-fn`, which receives the key and value and returns the transformed value:

```clojure
(defn my-value-reader [key value]
  (if (= key :date)
    (java.sql.Date/valueOf value)
    value))

(json/read-str "{\"number\":42,\"date\":\"2012-06-02\"}"
               :value-fn my-value-reader
               :key-fn keyword)
;;=> {:number 42, :date #inst "2012-06-02T04:00:00.000-00:00"}
```

Note the ordering subtlety documented in the README: when reading, `:value-fn` runs **after** the key has been processed by `:key-fn`; when writing, the reverse is true. And note the versioning philosophy: data.json follows MAJOR.MINOR.PATCH but explicitly does not follow semantic versioning — changes endeavor to be non-breaking "by moving to new names rather than by breaking existing names."

**The trade-off:** you trade convenience for transparency. There is no automatic `Date` encoding, so anything beyond maps/vectors/strings/numbers/bools is your responsibility. For library authors that is precisely the point: data.json will never ambush your users with a Jackson version conflict.

## Cheshire: The Batteries-Included Workhorse

Cheshire's origin story explains its design. Its author writes that *clojure-json had really nice features (custom encoders), but was slow; clj-json had no features, but was fast. Cheshire encodes JSON fast, with added support for more types and the ability to use custom encoders.* Current releases (6.2.0, on Jackson 2.21.1) add `Date`/`UUID`/`Set`/`Symbol` encoding and **SMILE** support — Jackson's binary JSON format — which makes Cheshire the only one of the three that speaks a binary dialect with the same API.

```clojure
(ns my.ns
  (:require [cheshire.core :refer :all]))

;; encode
(generate-string {:foo "bar" :baz 5})
;;=> "{\"foo\":\"bar\",\"baz\":5}"

(generate-string {:foo "bar" :baz {:eggplant [1 2 3]}} {:pretty true})

;; dates become strings with a configurable format
(generate-string {:baz (java.util.Date. 0)} {:date-format "yyyy-MM-dd"})

;; custom key munging on the way out
(generate-string {:foo "bar"} {:key-fn (fn [k] (.toUpperCase (name k)))})
;;=> "{\"FOO\":\"bar\"}"

;; binary JSON
(generate-smile {:foo "bar" :baz 5})

;; decode — pass true to keywordize
(parse-string "{\"foo\":\"bar\"}" true)
;;=> {:foo "bar"}

;; lazy parsing of huge documents
(parsed-seq (clojure.java.io/reader "/tmp/big.json"))
```

For genuinely exotic types, Cheshire's custom encoder registry lets you teach the encoder new classes globally:

```clojure
(ns myns
  (:require [cheshire.core :refer :all]
            [cheshire.generate :refer [add-encoder encode-str]]))

(add-encoder java.awt.Color
             (fn [c jsonGenerator]
               (.writeString jsonGenerator (str c))))
```

Cheshire is also a built-in library in **Babashka**, so any bb script can `(require '[cheshire.core :as json])` without adding a dependency. Between the type coverage, the forgiving `generate-string`/`parse-string` API, and the SMILE escape hatch, this is the library most Clojure projects reach for first — and the one most projects should keep.

**The trade-off:** `add-encoder` mutates global state, Jackson arrives as a heavyweight transitive dependency, and the kitchen-sink API makes it marginally slower than jsonista on hot paths.

## jsonista: Explicit Configuration, Maximum Throughput

jsonista comes from Metosin, the consultancy behind Reitit, Muuntaja, and most of the modern Clojure web toolchain. Its README positions it directly: *"Faster than data.json or Cheshire while still having the necessary features for web development."* The design choices are visible in the quickstart: functions are namespaced under `jsonista.core`, and the core abstraction is an explicit, reusable Jackson `ObjectMapper`:

```clojure
(require '[jsonista.core :as j])

(j/write-value-as-string {"hello" 1})
;;=> "{\"hello\":1}"

(j/read-value *1)
;;=> {"hello" 1}
```

The mapper is the star. For web services, where Clojure code conventionally uses keyword keys, jsonista ships a prebuilt mapper so you never hand-roll the common case:

```clojure
;; keyword-in, keyword-out mapper (the Ring/Reitit convention)
(-> {:dog {:name "Teppo"}}
    (j/write-value-as-bytes j/keyword-keys-object-mapper)
    (j/read-value j/keyword-keys-object-mapper))
;;=> {:dog {:name "Teppo"}}
```

Custom key transformation is expressed per-mapper rather than per-call, which both documents intent and avoids the global-registry smell:

```clojure
(defn reverse-string [s] (apply str (reverse s)))

(def mapper
  (j/object-mapper
    {:encode-key-fn (comp reverse-string name)
     :decode-key-fn (comp keyword reverse-string)}))

(j/write-value-as-string {:kikka "kukka"} mapper)
;;=> "{\"akkik\":\"kukka\"}"
```

The throughput claims come with receipts: the repository's JMH benchmarks show jsonista encoding a 10-byte payload at roughly **2 million ops/s versus about 1 million ops/s for Cheshire** on the same hardware, with the gap narrowing but persisting at larger payloads. Everything in the hot path is written in Java, protocol dispatch goes through `read-value`/`write-value`, and the library is designed to pair with Muuntaja for content negotiation in Ring applications. Java time types are supported through standard Jackson modules — add `jackson-datatype-jsr310` and register the module in your mapper for `Instant`/`LocalDate` round-tripping.

**The trade-off:** jsonista is lean by design — no SMILE, no global encoders, no implicit date formatting. It assumes you will configure a mapper once at startup, which is exactly right for a service boundary and slightly ceremonial for a throwaway script.

## Pitfalls: Where Each Library Bites

1. **String keys by default in all three.** If your code destructures `(:foo body)` against parsed JSON without keywordizing, you get `nil` and a confusing bug. The fix differs per library: `data.json` takes `:key-fn keyword`, Cheshire's `parse-string` takes a truthy second argument, and jsonista wants you to swap in `j/keyword-keys-object-mapper`. Decide your key convention at the namespace boundary, not in every handler.
2. **Keywordizing untrusted input leaks memory.** Keywords are interned and never garbage collected. If you `keywordize` keys of large attacker-controlled payloads, every distinct key becomes a permanent resident of the JVM — a classic slow-burn denial of service. Consider string keys at the edge and keywordize only after validation.
3. **Duplicate Jackson on the classpath.** Cheshire 6.2.0 pins Jackson 2.21.1; jsonista depends on its own jackson-databind version. Libraries that transitively pull both (a Ring stack using Cheshire for one thing and jsonista for another is common) can end up with two Jackson versions unless your build tool unifies them. Check `clj -Stree` / Leiningen dependency tree once and pin explicitly.
4. **Dates: nothing is automatic outside Cheshire.** jsonista needs the JSR-310 module registered in your mapper for `java.time` values, and data.json needs a handwritten `:value-fn` for every temporal type. Cheshire handles `java.util.Date` out of the box but emits it in a fixed default format (`yyyy-MM-dd'T'HH:mm:ss'Z'`) unless you pass `:date-format`.
5. **Global state in Cheshire custom encoders.** `add-encoder` registers process-wide. Two libraries in one app registering conflicting encoders for the same class will fight silently; prefer per-call `:key-fn`/`:value-fn` or a jsonista mapper for library code.
6. **Cheshire's pretty-printer is Jackson's, not yours.** If you need unusual array/object indentation, you must build a custom pretty-printer via `create-pretty-printer` with `default-pretty-print-options` — passing `{:pretty true}` only gets you the stock layout.
7. **Streams over strings for big files.** `parse-string` materializes the whole document. For multi-gigabyte exports use `parsed-seq` (Cheshire), `json/read` on a `Reader` (data.json), or jsonista's streaming docs — your heap will thank you.

## FAQ

### Which Clojure JSON library is fastest?

jsonista is the fastest of the three on encode and decode; its JMH benchmarks show roughly double Cheshire's throughput on small payloads, and both outrun data.json comfortably. For most applications the absolute difference is microseconds per request — jsonista's speed matters mainly on high-QPS API servers where JSON is the dominant cost.

### Is Cheshire the same as clj-json or clojure-json?

No — Cheshire was built *because* of their trade-offs: clojure-json had custom encoders but was slow, clj-json was fast but featureless. Cheshire merges both: Jackson-backed speed with custom encoders, extended type support, and SMILE.

### Can I use data.json in a library without forcing Jackson on my users?

Yes — that is its main selling point. data.json has zero external dependencies and is safe to ship inside libraries whose consumers are allergic to transitive framework baggage. The cost is manual `:key-fn`/`:value-fn` plumbing for anything beyond plain data.

### Does jsonista work with Ring and Reitit?

It is built for exactly that stack. Metosin's Muuntaja (the content-negotiation layer used with Reitit) uses jsonista under the hood, and `j/keyword-keys-object-mapper` produces the keyword-keyed maps Ring handlers conventionally expect. If you use Reitit + Muuntaja, you are already on jsonista.

### Is EPL-licensed JSON code OK for commercial projects?

Yes. The Eclipse Public License (EPL-1.0 for data.json, EPL-2.0 for jsonista) permits commercial use, modification, and redistribution. The main obligation: if you *modify and distribute* the library's own source files, you must make those modifications available under the EPL. Using it as a dependency in a proprietary application imposes no source-sharing requirement. Cheshire's MIT license is even less restrictive. All three are safe for proprietary products.

### Which library does Babashka use?

Babashka ships Cheshire built in, so scripts can `(require '[cheshire.core :as json])` with zero dependency declarations. For plain-JVM scripting without Babashka, data.json keeps your classpath clean.

### How do I handle java.time Instant and LocalDate?

jsonista: add `jackson-datatype-jsr310` and register the `JavaTimeModule` in your `object-mapper`. Cheshire: encode `java.util.Date` with `:date-format`, or register your own encoder for `java.time` types. data.json: write a `:value-fn`/`:key-fn` pair that converts to and from strings on the way out and in.

### Do I need SMILE?

Only if you control both ends of the wire and want a compact binary format with the same Jackson codec — Cheshire's `generate-smile`/`parse-smile` make this trivial. If you are interoperating with non-JVM clients, standard JSON is the safer default.

## The Verdict

The Clojure JSON ecosystem has matured into three clearly differentiated tools rather than three interchangeable ones. **data.json** is the principled minimal core: zero deps, strict spec compliance, and an honest "you do the type mapping" contract — perfect for libraries and dependency-conscious projects. **Cheshire** is the pragmatic default: rich type coverage, custom encoders, SMILE, Babashka support, and an API that gets out of your way — the right choice when JSON is a means to an end. **jsonista** is the performance-focused specialist: explicit mappers, Java-speed hot paths, and first-class citizenship in the Metosin web stack — the right choice when JSON parsing is measurable fraction of your request latency. If your Clojure services consume or produce JSON on the web, our [Clojure HTTP client comparison](../2026-09-07-clojure-http-clients-clj-http-httpkit-hato-comparison/) covers the transport layer these libraries feed, and the [Ring vs Compojure vs Reitit framework guide](../2026-08-29-ring-vs-compojure-vs-reitit-clojure-web-framework-comparison/) shows where Muuntaja's jsonista integration plugs into routing. For a cross-language perspective on the same problem, the [Erlang JSON libraries comparison](../2026-09-05-erlang-json-libraries-jiffy-jsx-jsone-comparison/) demonstrates how another JVM-adjacent ecosystem solved parsing-speed trade-offs.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Clojure JSON Libraries in 2026: Cheshire vs jsonista vs data.json",
  "description": "In-depth comparison of the three main Clojure JSON libraries: Cheshire (feature-rich Jackson wrapper), jsonista (Metosin's high-performance mapper), and data.json (zero-dependency minimal core), with real code examples and benchmarks.",
  "datePublished": "2026-09-08",
  "dateModified": "2026-09-08",
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
