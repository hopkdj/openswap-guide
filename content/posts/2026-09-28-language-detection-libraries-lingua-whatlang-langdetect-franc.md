---
title: "lingua vs whatlang vs langdetect vs franc in 2026: Which Language Detector Should You Trust?"
date: "2026-09-28"
tags: ["python", "rust", "javascript", "text-processing", "comparison"]
draft: false
cover: "/img/screenshots/lingua-logo.jpg"
description: "Language detection libraries compared with live 2026 repository data and real API examples: lingua, whatlang, langdetect and franc, plus two popular archives you should stop using."
---

Detecting the language of a piece of text looks like a solved problem until you try it on real data. A support ticket that says "merci" gets classified as French. A product review that says "ok" gets classified as Dutch. A mixed-language chat message gets one confident — and wrong — answer. Then you discover that two of the libraries everyone recommends are **archived on GitHub**, and the one your team chose last year has not been touched since 2022.

This comparison uses repository data pulled on **2026-09-28** and API examples taken directly from each project's own documentation, so you can pick a detector that is still maintained and know exactly how it behaves on short strings.

## TL;DR: Quick Verdict

- **You need the highest accuracy, especially on short text → `lingua`.** It is the only library here that was designed for short and mixed-language input, it is actively developed in both Rust and Python, and it exposes confidence thresholds so you can return "unknown" instead of guessing.
- **You need raw speed in Rust and a simple reliability flag → `whatlang`.** It also reports the *script* (Latin, Cyrillic, and so on), which is often more useful than a language label on its own.
- **You are already in Python and want the smallest possible change → `langdetect`.** It has the most stars of the Python options and a trivial API, but its last commit was **2025-03-03** and its model can vary between runs unless you seed it.
- **You need to cover hundreds of languages in Node → `franc`.** It supports the widest range by far (82, 187 or 414 languages depending on package), but it has been dormant since **2024-06-12** and its own documentation warns it is "easily confused on small samples."

## The Contenders at a Glance

All repository data fetched **2026-09-28**.

| | **lingua** | **whatlang** | **langdetect** | **franc** |
|---|---|---|---|---|
| Repository | `pemistahl/lingua-rs` / `lingua-py` | `greyblake/whatlang-rs` | `Mimino666/langdetect` | `wooorm/franc` |
| Stars | 1,142 (Rust) / 1,805 (Python) | 1,088 | 1,904 | **4,416** |
| Last commit | **2026-09-18** (Rust), 2026-07-20 (Python) | 2025-12-24 | 2025-03-03 | 2024-06-12 |
| Language | Rust + Python | Rust | Python | JavaScript (ESM) |
| Languages supported | 75+ | 69 | 55 | **82 / 187 / 414** |
| Short-text handling | Purpose-built | Good, with reliability flag | Weak | Weak (needs long input) |
| Confidence output | Relative distances, confidences | `confidence()` + `is_reliable()` | Probabilities per language | None |
| Script detection | Via language model | **Yes** (`Script`) | No | No |
| Install | `cargo add lingua` / `pip install lingua-language-detector` | `cargo add whatlang` | `pip install langdetect` | `npm install franc` |

For reference, the two libraries you will still find recommended in older tutorials are **`google/cld3` (archived 2023-05-24)** and **`facebookresearch/fastText` (archived 2024-03-22)**. Both were impressive statistical classifiers, but an archived repository receives no fixes. Do not start new work on them.

## Decision Matrix: Pick in Ten Seconds

| Your situation | Choose | Why |
|---|---|---|
| Support tickets, chat messages, anything under 20 words | **lingua** | Designed for short text; supports a minimum-distance threshold |
| High-volume batch classification in Rust | **whatlang** | Lightweight, 100% Rust, includes a reliability flag |
| Quick Python script, no build toolchain beyond pip | **langdetect** | Two-line API; extremely low setup cost |
| Node service covering rare languages | **franc-all** | 414 languages, with `franc-min` for a much smaller footprint |
| Mixed-language documents | **lingua** | `detect_multiple_languages_of` handles multi-language input |
| You must return "unknown" instead of guessing | **lingua** or **whatlang** | Both expose a way to express uncertainty |

## lingua — Accuracy First, in Rust and Python

**1,142 stars (Rust) · 1,805 stars (Python) · last commit 2026-09-18 · Apache-2.0**

lingua's README describes it as *"The most accurate natural language detection library for Rust, suitable for short text and mixed-language text."* That second clause is the differentiator: most detectors were tuned on paragraphs, and fall apart on the two-word queries that dominate real application data.

The Rust API, straight from the project's documentation:

```toml
[dependencies]
lingua = { version = "1.8.0", default-features = false, features = ["french", "italian", "spanish"] }
```

```rust
use lingua::{Language, LanguageDetector, LanguageDetectorBuilder};

let languages = vec![Language::English, Language::French, Language::German, Language::Spanish];
let detector: LanguageDetector = LanguageDetectorBuilder::from_languages(&languages).build();
let detected_language: Option<Language> = detector.detect_language_of("languages are awesome");
```

Notice `default-features = false` plus an explicit feature list. Every language you enable adds model data to your binary, so **enabling only what you need is a real deployment decision**, not a micro-optimisation. If you genuinely need everything:

```rust
LanguageDetectorBuilder::from_all_languages().with_preloaded_language_models().build();
```

`with_preloaded_language_models()` trades memory for latency by loading models at build time instead of on first use — worth it for a long-running server, wasteful for a CLI that exits immediately. There is also a `with_low_accuracy_mode()` for cases where speed matters more than precision.

The mechanism that makes lingua usable in production is the minimum relative distance:

```rust
let detector = LanguageDetectorBuilder::from_languages(&[English, French, German, Spanish])
    .with_minimum_relative_distance(0.9)
    .build();

let detected_language = detector.detect_language_of("languages are awesome");
```

With a threshold of `0.9`, ambiguous input returns `None` rather than a confident wrong answer. **That single option is why lingua is the right default for user-facing features** — a "we could not determine the language" response is far better than mislabelling a customer's message.

The Python port mirrors the same design:

```bash
pip install lingua-language-detector
```

```python
from lingua import Language, LanguageDetectorBuilder

languages = [Language.ENGLISH, Language.FRENCH, Language.GERMAN, Language.SPANISH]
detector = LanguageDetectorBuilder.from_languages(*languages).build()
language = detector.detect_language_of("languages are awesome")
```

The Python build ships platform wheels, and the documentation notes an offline installation path (`pip install --find-links=lingua lingua-language-detector`) for air-gapped environments. For mixed-language input, `detect_multiple_languages_of` returns results per span rather than one label for the whole document, and parallel variants such as `detect_languages_in_parallel_of` exist for throughput. You can also build restricted detectors — `from_all_languages_with_cyrillic_script()` or `from_all_languages_without(Language.SPANISH)` — which is a genuinely practical way to cut both binary size and false positives.

![lingua official project logo](/img/screenshots/lingua-logo.jpg "lingua language detection library official logo")

## whatlang — Fast, Lightweight, and Honest About Uncertainty

**1,088 stars · last commit 2025-12-24 · MIT**

whatlang's README lists four selling points: it is **100% written in Rust**, lightweight, fast and simple, it recognises the **script** in addition to the language, and it provides reliability information. The complete example from the documentation:

```rust
use whatlang::{detect, Lang, Script};

fn main() {
    let text = "Ĉu vi ne volas eklerni Esperanton? Bonvolu! Estas unu de la plej bonaj aferoj!";

    let info = detect(text).unwrap();
    assert_eq!(info.lang(), Lang::Epo);
    assert_eq!(info.script(), Script::Latin);
    assert_eq!(info.confidence(), 1.0);
    assert!(info.is_reliable());
}
```

Two API details earn it a place in production pipelines. First, **`script()` is often more actionable than `lang()`**: knowing text is Cyrillic immediately narrows your detector's candidate set, and for routing decisions a script is frequently all you need. Second, **`is_reliable()` gives you a single boolean** to gate downstream behaviour, and `confidence()` gives you the underlying number when you want to tune a threshold yourself.

whatlang is also the easiest of the four to embed in a larger Rust service: no model files to ship, no feature flags to juggle, and it compiles to something small. The trade-off is scope — 69 languages versus lingua's stricter accuracy guarantees on very short input.

The project publishes its own accuracy analysis in the repository, which is a rare and welcome level of transparency:

![whatlang reliability benchmark chart published in the official repository](/img/screenshots/whatlang-benchmark.jpg "whatlang reliability benchmark published in its official repository")

## langdetect — The Python Default, With Two Caveats

**1,904 stars · last commit 2025-03-03 · Apache-2.0**

langdetect is a port of Google's language-detection library to Python, and its API is as small as it gets:

```bash
pip install langdetect
```

```python
>>> from langdetect import detect
>>> detect("War doesn't show who's right, just who's left.")
'en'
>>> from langdetect import detect_langs
>>> detect_langs("Otec matka syn.")
```

`detect_langs` returns probabilities rather than a single label, which is what you want when you plan to apply your own threshold. Two caveats matter in practice.

**First, results are non-deterministic by default.** The documentation's own workaround is:

```python
from langdetect import DetectorFactory
DetectorFactory.seed = 0
```

Without that seed, the same input can produce different probability distributions across runs, because the underlying algorithm performs random sampling. If your tests assert on detection output — or if you cache results — set the seed explicitly.

**Second, the maintenance signal is soft.** The last commit was **2025-03-03**, comfortably over a year before this comparison. That is not abandoned, but it is not active either. For a small internal script, that is fine. For a service that governs how user content is routed, prefer lingua, whose short-text handling is also stronger out of the box.

## franc — Widest Language Coverage, Longest Silence

**4,416 stars · last commit 2024-06-12 · MIT**

franc has the highest star count of the four and the widest language coverage, and its README is unusually candid about both strengths and weaknesses. On the positive side, it can support more languages than any comparable library, packaged in three sizes: **82 languages** (`franc-min`, 8M+ speakers), **187 languages** (the default `franc` package), and **419 languages** (`franc-all`). It also ships a CLI.

```bash
npm install franc
```

The README's own caution is the part most teams skip: *"franc supports many languages, which means it's easily confused on small samples. Make sure to pass it big documents to get reliable results."* If your input is chat messages or search queries, that sentence should disqualify franc immediately — this is a detector for documents, not fragments.

Two operational notes. franc is **ESM-only**, so a CommonJS codebase needs either a dynamic `import()` or a migration; the documentation states Node 14.14+ / 16.0+. And the last commit was **2024-06-12**, roughly two years before this comparison, so treat it as frozen: pin the version, use `franc-min` when you can, and do not expect fixes.

## Pitfalls and Migration Traps

**1. Judging a detector on long documents.** Every library here looks accurate on a paragraph. The differences appear at 3–10 words, which is exactly where production traffic lives. Benchmark on *your* shortest inputs before choosing.

**2. Ignoring the language-model subset.** lingua's feature flags and franc's three package sizes exist because model data dominates the footprint. Shipping all 75+ languages when your product supports five is a self-inflicted latency and size problem.

**3. Forgetting the non-determinism in langdetect.** Without `DetectorFactory.seed = 0`, repeated runs can disagree. This produces flaky tests and cache misses that are maddening to debug.

**4. Building on archived dependencies.** `google/cld3` (archived 2023-05-24) and `facebookresearch/fastText` (archived 2024-03-22) still appear in tutorials and blog posts. They work, but nobody is patching them.

**5. Treating detection as a hard classification.** The correct production pattern is a **confidence threshold with an "unknown" outcome**. lingua's `with_minimum_relative_distance()` and whatlang's `is_reliable()` both give you that; a bare `detect()` call does not.

**6. Assuming one label per document.** Real content mixes languages — quoted strings, product names, code. lingua's `detect_multiple_languages_of` handles this; the others generally return a single dominant label.

**7. Skipping the script check.** For many routing tasks, knowing the script is enough and is far more reliable than a language guess. If you only need to separate Cyrillic from Latin input, you do not need a full detector.

## Related Reading on Text Pipelines

Language detection usually sits in the middle of a larger text pipeline, and the surrounding stages are worth getting right. Our comparison of [spell-checking engines](../2026-09-25-spell-checking-engines-hunspell-nuspell-symspell-codespell/) covers dictionary-driven correction applied to the same raw input, and explains why Unicode normalisation has to happen before any dictionary lookup. Our guide to [probabilistic data structures](../2026-06-19-probabilistic-data-structures-bloom-cuckoo-hyperloglog-countmin/) shows the approximate structures that keep high-volume text processing cheap — the same reasoning applies when you cache detection results at scale. And if detection feeds a search box, the [client-side fuzzy search comparison](../2026-08-18-fusejs-vs-minisearch-vs-lunrjs-client-side-fuzzy-search-comparison/) covers what happens after you have decided which language the query is in.

## FAQ

**Which language detection library is most accurate on short text?**
lingua, by design. It was built specifically for short and mixed-language input, and it is the only library here that exposes a minimum relative distance, letting you reject ambiguous results instead of guessing. For queries of three to ten words, that design difference matters more than any benchmark average.

**Is langdetect still maintained?**
Barely. Its last commit was **2025-03-03**, over a year before this comparison. It still works and has the largest star count among the Python options, but it receives little active development. For new Python services, lingua's Python port is the safer long-term choice.

**Why does langdetect give different answers for the same input?**
Because its algorithm performs random sampling, so probability output varies between runs. The documented fix is `DetectorFactory.seed = 0`, which makes detection deterministic. Set it if you cache results or assert on output in tests.

**How many languages can franc detect?**
Up to **419** with `franc-all`, 187 with the default `franc` package, and 82 with `franc-min`. The cost is accuracy on short input — franc's own documentation warns it is easily confused on small samples.

**Can a language detector tell me the script instead of the language?**
Yes, and it is often more useful. whatlang returns a `Script` value (Latin, Cyrillic, and others) alongside the language, which is enough for routing decisions and considerably more reliable than a language label on very short text.

**Should I self-host detection or call an external service?**
For anything at volume, self-host. All four libraries run in-process with no network round trip, and the recurring cost is zero. The trade-off is model size and memory: lingua with preloaded models for many languages is the heaviest configuration here, so restrict the language set to what your product actually supports.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "lingua vs whatlang vs langdetect vs franc in 2026: Which Language Detector Should You Trust?",
  "description": "Language detection libraries compared with live 2026 repository data and real API examples: lingua, whatlang, langdetect and franc, plus two archived libraries to avoid.",
  "datePublished": "2026-09-28",
  "dateModified": "2026-09-28",
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
