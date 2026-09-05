---
title: "Clojure Data Validation in 2026: Malli vs Schema vs clojure.spec — Which Should You Use?"
date: "2026-09-05"
tags: ["clojure", "data-validation", "developer-tools", "functional-programming"]
draft: false
---

Clojure 1.9 shipped `clojure.spec` back in 2018 as the community's answer to "what if function arguments were validated by design?" — and yet, eight years later, the validation question is *more* contested than ever. Today you have three production-grade options: **Malli** (1,765 stars, actively developed by Metosin), **plumatic/schema** (2,462 stars, the elder statesman), and **clojure.spec** itself (bundled with the language, backed by Clojure core). Each one encodes a completely different philosophy about how data should be described, and picking wrong means rewriting your entire data layer a year from now.

Here's the uncomfortable truth: none of the three is objectively "best." They disagree on fundamentals — whether schemas are macros or plain data, whether validation happens at the function boundary or wherever you call it, and whether a schema should be serializable to JSON Schema. This guide gives you the decision framework, the real code, and the migration traps so you can pick once and move on.

**TL;DR:** If you need runtime-editable schemas, JSON Schema / OpenAPI interop, or ClojureScript support, choose **Malli**. If you maintain an older codebase that already standardizes on data-literal schemas, stay on **plumatic/schema** — it's stable, proven, and still maintained. If you want zero extra dependencies, generative testing at function boundaries, and you're comfortable with macros plus a global registry, **clojure.spec** is the stdlib answer. My recommendation for new projects in 2026: **Malli**, because data-driven schemas compose with the rest of your data-driven architecture in ways the other two can't match.

## The Three Philosophies in One Table

| Dimension | Malli | plumatic/schema | clojure.spec |
|---|---|---|---|
| First release | 2021 (metosin/malli) | 2013 (plumatic/schema) | 2016 alpha, 2018 in Clojure 1.9 |
| Schema representation | Plain data (vectors/maps) | Plain data (Clojure data literals) | Macros + global registry (`s/def`) |
| Latest release | 0.20.1 (2026-03-06) | 1.3.4 (tags) | Ships with Clojure core |
| GitHub activity | Pushed 2026-09-04 | Pushed 2026-08-09 | spec.alpha repo pushed 2026-01 |
| Stars | 1,765 | 2,462 | Clojure repo 10,956 (spec is core) |
| License | EPL-2.0 | EPL-1.0 | EPL-1.0 |
| ClojureScript | First-class | First-class | Supported |
| JSON Schema export | Native (`m/->json-schema`) | Via separate tooling | Not provided |
| OpenAPI/Swagger | Native via malli + Metosin stack | Manual | Not provided |
| Runtime schema editing | Yes | Limited | No |
| Generative testing | `malli.generator` (test.check based) | `schema-generators` (experimental) | `s/gen` — best-in-class |
| Function instrumentation | Optional (`malli.instrument`) | Manual wrappers | `s/instrument` — first-class |
| Error output | Structured data + human text | Human text with data shape | Human text |

## Use Case → Decision Matrix

| Use Case | Recommended Tool | Reason |
|---|---|---|
| New Clojure service with a public JSON API | Malli | Native JSON Schema / OpenAPI export keeps docs and validation in sync |
| Multi-tenant app where tenants edit schemas at runtime | Malli | Schemas are plain data — persist them, load them, validate against them |
| Legacy system built on schema since 2014 | plumatic/schema | 2,462 stars and a decade of battle testing; migration cost isn't worth it |
| Pure Clojure library that must stay dependency-free | clojure.spec | Part of the language; predicates compose with `s/and`, `s/or`, `s/keys` |
| You want generative testing as the *primary* testing strategy | clojure.spec | `s/gen` + `stest/summarize-results` is the most mature property-testing story |
| Team of Clojure newcomers, JSON background | Malli | Vector syntax reads like JSON Schema with less ceremony |
| ClojureScript + re-frame front end sharing schemas with the backend | Malli or schema | Both cross-compile cleanly; spec registry state is clumsier in cljs |

## Malli 0.20: Data-Driven Schemas for the Modern Stack

Malli was born from a very specific frustration. Metosin maintained `spec-tools` for five years — a compatibility layer that tried to give clojure.spec runtime transformation and JSON Schema support — and eventually concluded it was "still a kind of hack and not fun to maintain." So they started fresh with a design where a schema is literally data, not a macro call:

```clojure
(require '[malli.core :as m])

(def UserId :string)

(def Address
  [:map
   [:street :string]
   [:country [:enum "FI" "UA"]]])

(def User
  [:map
   [:id #'UserId]
   [:address #'Address]
   [:friends [:set {:gen/max 2} [:ref #'User]]]])
```

Because schemas are data, you can `def` them, compose them, transform them, and — critically — persist them. The same schema drives validation, value generation, and API documentation:

```clojure
(require '[malli.generator :as mg])

(mg/generate User)
;{:id "AC",
; :address {:street "mf", :country "UA"},
; :friends #{{:id "1dm", :address {:street "8", :country "UA"}, :friends #{}}}}

(m/validate User *1)
; => true
```

Where Malli really pulls ahead is error reporting. `m/explain` returns *structured* errors — a vector of maps with `:path`, `:in`, `:schema`, and `:value` keys — that you can render in a UI, log as JSON, or use to build field-level form errors:

```clojure
(m/explain
  Address
  {:id "Lillan"
   :tags #{:artesan "coffee" :garden}
   :address {:street "Ahlmanintie 29"
             :zip 33100
             :lonlat [61.4858322 nil]}})
;; => {:errors ({:path [:tags 0], :in [:tags 0], :schema :keyword, :value "coffee"}
;;              {:path [:address :city], :type :malli.core/missing-key}
;;              {:path [:address :lonlat 1], :schema :double, :value nil})}
```

The value of structured errors shows up the moment you build a form validator or an API error body. clojure.spec gives you a string; schema gives you a string; Malli gives you data your code can act on.

Malli 0.20.1 (March 2026) requires Clojure 1.11+ and is tested against the LTS Java releases 8, 11, 17, 21, and 25. The repo was pushed as recently as September 2026, and it integrates with the wider Metosin stack — Reitit uses it for coercion out of the box, which is why teams already on Ring + Reitit tend to adopt Malli without a second thought.

## plumatic/schema: The Proven Workhorse

Schema predates spec by five years and, in many ways, spec was a response to its limitations. Its core idea: a schema is a Clojure data structure that looks like the data it describes. `s/defschema` documents a shape; `s/validate` checks a value against it:

```clojure
(ns schema-examples
  (:require [schema.core :as s]))

(s/defschema Data
  "A schema for a nested data type"
  {:a {:b s/Str
       :c s/Int}
   :d [{:e s/Keyword
        :f [s/Num]}]})

(s/validate
  Data
  {:a {:b "abc" :c 123}
   :d [{:e :bc :f [12.2 13 100]}]})
;; Success!

(s/validate
  Data
  {:a {:b 123 :c "ABC"}})
;; Exception -- Value does not match schema:
;;  {:a {:b (not (instance? java.lang.String 123)),
;;       :c (not (integer? "ABC"))},
;;   :d missing-required-key}
```

Simple schemas compose exactly like the data they describe — a list of strings is `[s/Str]`, a nested map is `{long {String double}}`:

```clojure
(s/validate [s/Str] ["a" "b" "c"])

(def StringList [s/Str])
(s/defschema StringList [s/Str])

(s/validate StringList ["a" :b "c"])
;; RuntimeException: Value does not match schema:
;;  [nil (not (instance? java.lang.String :b)) nil]
```

Schema's strengths are boring in the best way: it has been in production for over a decade, its error messages show you the offending slice of data, and version 1.3.4 remains the stable line. The repo is still receiving maintenance pushes (August 2026). Its weaknesses are equally well documented: no built-in JSON Schema export, no runtime transformation story, and schema composition for polymorphic data gets verbose. Malli's own README pays it respect — "an awesome, proven and collaborative open-source project" — while explaining precisely why Metosin built something new: "serializing & de-serializing schemas is non-trivial and there is no proper support on branching."

If your codebase already has 50 `s/defschema` blocks, don't migrate for fashion. Schema is not abandoned, and rewriting working validation is how you introduce bugs. Adopt Malli for *new* modules and keep schema for the legacy core.

## clojure.spec: The Standard Library Option

Spec shipped inside Clojure 1.9 and is the only option with zero dependency cost. It validates predicates — ordinary functions — composed into specs, and it has two features neither rival fully matches: `s/instrument` for checking function call sites at runtime, and `s/gen` for deriving generators straight from specs.

At the data level, spec validates like this:

```clojure
(require '[clojure.spec.alpha :as s])

(s/valid? even? 10)
;;=> true

(s/conform even? 1000)
;;=> 1000
```

Real specs are built from keywords registered in a global registry, using `s/def` plus combinators like `s/and`, `s/or`, and `s/keys`:

```clojure
(s/def ::age (s/and int? #(> % 0)))
(s/def ::name string?)

(s/valid? ::age 42)   ;=> true
(s/valid? ::age -1)   ;=> false
(s/explain ::age -1)  ; prints a human-readable failure report
```

The macro-plus-registry design is where spec becomes controversial. Because specs live in a global namespace-keyed registry, two libraries can collide on names, and spec definitions are compile-time artifacts — you can't easily persist a spec, send it over the wire, or edit it at runtime. Spec's generative testing is genuinely excellent (wrap any spec in `s/gen` and feed it to `test.check`), and `s/instrument` is the cleanest function-contract enforcement of the three. But JSON Schema export was never provided, which matters enormously for HTTP APIs.

The elephant in the room: a ground-up rewrite (spec 2, in the `clojure/spec-alpha2` repo) has been in alpha for years — last pushed December 2025 — without a stable release, leaving spec.alpha users in limbo about the ecosystem's direction. Spec remains the right call for libraries that must stay dependency-free and for teams that want property testing as a core practice. For web services that need to document and validate the same shape, Malli's JSON Schema story wins.

## Schema Transformations: The Hidden Decider

Most validation shootouts stop at "does it validate?" — but in 2026, the deciding question is "can the schema leave the JVM?" API documentation, client code generation, form builders, and data-contract registries all want your schema in an interoperable format.

Malli treats this as a core feature: schemas transform to JSON Schema, Swagger 2.0, and plain-English descriptions, and the same schema drives both request coercion and response generation in Reitit. This is the single biggest practical gap between Malli and its rivals. If your team ships a JSON API, "schema as data that serializes to JSON Schema" collapses an entire class of documentation-drift bugs. Schema tooling exists but is fragmented; spec has no first-party path at all.

## Migration Pitfalls: What Nobody Tells You

1. **Validate at the edges, not everywhere.** All three libraries let you sprinkle validation through every function — don't. Validate at API boundaries, message consumers, and persistence layers. Spec's `s/instrument` exists precisely to check internal contracts without hand-placed calls.
2. **Macro vs data is a migration cliff.** Moving spec's `s/def`-style registries to Malli means rewriting specs as data — it's mechanical, but your `s/keys` and `s/or` shapes map to `[:map [:key]]` and `[:orn]` differently than you'd guess. Budget a week for a serious codebase.
3. **Registry collisions are real.** Spec's global registry means two libraries defining `::id` can clobber each other. Malli and schema avoid this entirely by keeping schemas in your own vars.
4. **Error-handling code differs by an order of magnitude.** If you plan to render field-level errors in a UI, Malli's structured `:errors` vector is worth more than any feature comparison suggests. String-parsing spec or schema error output is a maintenance trap.
5. **Don't trust "schema valid" to mean "safe to persist."** Validation confirms shape, not semantics. A `:string` email that passes schema validation can still be garbage — pair validation with content rules.
6. **ClojureScript parity check.** All three cross-compile, but spec's registry state and instrumentation behave differently in the browser. For re-frame apps sharing schemas with a backend, data-driven Malli schemas survive serialization cleanly.
7. **Generative testing expectations.** Spec generates from specs out of the box; Malli needs `malli.generator` plus `gen/max` hints for recursive schemas; schema's generation support was always experimental. If property testing is your goal, spec is still the smoothest path.
8. **Version pinning.** Malli moves fast (0.20.x line). Schema 1.3.x barely changes — which is a feature for stability-focused teams. Choose based on how much churn your team tolerates.

For more on the Clojure ecosystem's evolution, see our [Clojure async libraries comparison](../2026-09-04-clojure-async-libraries-core-async-manifold-aleph-comparison/) and the [Ring vs Compojure vs Reitit web framework guide](../2026-08-29-ring-vs-compojure-vs-reitit-clojure-web-framework-comparison/). If you're coming from the JavaScript world, our [TypeScript schema validation shootout](../2026-07-24-typescript-schema-validation-typebox-arktype-runtypes/) and the [Zod vs Valibot vs Yup comparison](../2026-08-12-zod-vs-valibot-vs-yup-typescript-schema-validation-comparison/) cover the same decision from that ecosystem's perspective.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Clojure Data Validation in 2026: Malli vs Schema vs clojure.spec — Which Should You Use?",
  "description": "Deep comparison of Clojure's three data validation libraries in 2026: Malli (data-driven, JSON Schema interop), plumatic/schema (proven workhorse), and clojure.spec (stdlib, generative testing). Includes decision matrix, real code examples, and migration pitfalls.",
  "datePublished": "2026-09-05",
  "dateModified": "2026-09-05",
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

**Is clojure.spec being replaced by spec 2?**
The clojure/spec-alpha2 repository remains in alpha with no stable release as of late 2025 — the last push was December 2025. Production teams should treat spec.alpha (shipped with Clojure core) as the stable option and watch spec 2 for the future, or choose Malli if they need capabilities spec doesn't provide today.

**Can Malli and clojure.spec coexist in one project?**
Yes. Many teams use spec for function instrumentation and generative testing on internal logic while adopting Malli for API-facing schemas. Malli even supports wrapping spec predicates as schema types, so the boundary is porous.

**Which library has the best performance?**
Malli is generally the fastest of the three in microbenchmarks thanks to compiled schema paths, followed by schema. Spec's macro-expanded predicates are competitive but its explain path allocates more. For typical web request validation, all three are fast enough — correctness and ergonomics matter more than nanoseconds.

**Does plumatic/schema still work with current Clojure versions?**
Yes. Schema 1.3.x runs on modern Clojure (1.10+ through 1.12) and ClojureScript, and the repository received maintenance activity as recently as August 2026. It's not abandoned, just stable.

**Which option is best for a ClojureScript front end?**
Malli and schema both cross-compile cleanly and let you share schema definitions between client and server. Spec works in ClojureScript but the global registry and instrumentation story is clumsier. If you're serializing schemas to send to the browser, data-driven Malli is the cleanest.

**Do I need JSON Schema export?**
If you expose a public JSON API, generate client SDKs, or feed schemas into documentation tools, yes — and only Malli provides this natively. Schema and spec leave you building (or maintaining) export tooling yourself.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
