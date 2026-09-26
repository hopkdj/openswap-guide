---
title: "Pluralization Libraries in 2026: inflect vs pluralize vs evo-inflector vs go-pluralize"
date: "2026-09-26"
tags: ["i18n", "developer-libraries", "developer-tools", "python", "javascript", "java", "go", "rust", "text-processing"]
draft: false
description: "Pluralization and inflection libraries compared with live 2026 data: inflect 7.5.0, pluralize 8.0.0, evo-inflector 2.0, go-pluralize and Rust Inflector — with real code, accuracy numbers, and the uncountable-word trap."
---

## "You Have 1 Items"

It appears in the first hour of a new project and then lives in the UI for years: `1 items`, `3 childs`, `5 categorys`. English inflection looks like a one-line function until you meet *children*, *people*, *geese*, *data*, *series* and the entire uncountable category, at which point you are maintaining a rule list — badly — instead of shipping.

There are five established libraries that already maintain that rule list for you, and 2026 gave them a real shake-up: **evo-inflector** shipped a 2.0 rewrite around a compiled matching engine, while the JavaScript original (**pluralize**, 2,216★) has not been pushed since June 2024. Here is what each one actually does, with numbers pulled live from GitHub, PyPI, npm and Maven.

**TL;DR — Quick Verdict:** In Python, **inflect** (7.5.0) — it handles nouns, verbs, adjectives, ordinals, indefinite articles and number-to-words in one engine. In JavaScript, **pluralize** (8.0.0) is still the standard API, stale push date and all. In Java, **evo-inflector 2.0** is the clear pick, backed by Wiktionary accuracy data and a large production install base. In Go, **go-pluralize** — a faithful port of the JavaScript rule set, so the two agree on output. And note what none of them are: a substitute for locale-aware plural formatting in user-facing translations.

## The Five Contenders at a Glance

| Library | Language | Stars | Last push | Latest version | Install | License |
|---|---|---|---|---|---|---|
| pluralize | JavaScript | 2,216 | 2024-06-26 | 8.0.0 (npm) | `npm install pluralize --save` | MIT |
| inflect | Python | 1,083 | 2026-04-13 | 7.5.0 (PyPI) | `pip install inflect` | MIT |
| evo-inflector | Java | 346 | 2026-07-24 | 2.0 (Maven) | Maven `org.atteo:evo-inflector` | Apache-2.0 |
| go-pluralize | Go | 171 | 2025-12-14 | v0.2.0 | `go get -u github.com/gertd/go-pluralize` | MIT |
| Inflector | Rust | 129 | 2023-06-03 | crate `inflector` | `Inflector = "*"` in `[dependencies]` | BSD-2-Clause |

## Decision Matrix: Pick in Ten Seconds

| Your situation | Pick | Why |
|---|---|---|
| Python CLI printing counts | **inflect** | `p.plural_noun("person", count)` plus `p.no(" error", count)` |
| Python, need verb agreement too | **inflect** | `plural_verb("was", count)` handles "was/were" |
| Node.js or browser | **pluralize** | `pluralize('test', count)` — the de facto API |
| Java / Spring codebase | **evo-inflector** | Pluralization only, but battle-tested and now much faster |
| Go service mirroring Node rules | **go-pluralize** | Explicitly tracks the npm package version it ports |
| Rust, plus case conversions | **Inflector** | Pluralize *and* snake/camel/kebab/class-case helpers |
| User-facing translated text | none of these | Use gettext or ICU plural rules per locale |
| Database table or class naming | **Inflector** / **evo-inflector** | Deterministic English rules are exactly right here |

## inflect — Python's Inflection Toolkit

inflect 7.5.0 is the deepest of the five, because it is not only about nouns.

```bash
pip install inflect
```

```python
import inflect
p = inflect.engine()

"the plural of person is " + p.plural("person")
# 'the plural of person is people'
```

The count argument is what turns it into correct UI text — pass the number and the function picks the form:

```python
"the plural of 1 person is " + p.plural("person", 1)
# 'the plural of 1 person is person'
```

Beyond `plural()`, the engine exposes the family of methods you actually need: `plural_noun`, `plural_verb`, `plural_adj`, `singular_noun`, `no`, and `num`. A single sentence can exercise all of them:

```python
count = 3
print('There', p.plural_verb('was', count), p.number_to_words(count),
      p.plural_noun('person', count), 'by the door.')
# There were three people by the door.
```

This is why inflect wins the Python slot for anything textual: `plural_verb('was', 3)` producing *were* is not a noun rule, and `number_to_words` removes a second dependency. `p.no(" error", count)` is the idiomatic way to build count-aware labels without an `if count == 1` branch, and `singular_noun("people")` reverses the direction when you are normalizing input from users.

## pluralize — The JavaScript Standard, Frozen but Fine

pluralize 8.0.0 defines the API that everyone else copies.

```bash
npm install pluralize --save
```

```javascript
pluralize('test')       //=> "tests"
pluralize('test', 0)    //=> "tests"
pluralize('test', 1)    //=> "test"
pluralize('test', 5)    //=> "tests"
pluralize('test', 1, true) //=> "1 test"
pluralize('test', 5, true) //=> "5 tests"
pluralize('蘋果', 2, true) //=> "2 蘋果"
```

That third argument is the useful one: `pluralize(word, count, true)` returns the count *and* the correctly inflected word in one string, which is precisely the `1 item` / `5 items` label you were writing by hand. The README's Unicode example — Chinese characters passed through with the count prepended — shows the library only inflects what has English rules and leaves the rest alone, which is the correct behaviour for mixed content.

Custom vocabulary is where the API earns its keep:

```javascript
pluralize.addPluralRule(/gex$/i, 'gexii');
pluralize.addIrregularRule('irregular', 'regular');
pluralize.isPlural('test'); //=> false
```

`addIrregularRule` is the escape hatch for product names and domain nouns that the general rules get wrong — renames, brands, internal jargon. Every long-lived codebase ends up with a few of those.

The trade-off to accept consciously: **the package was last pushed in June 2024.** It is not abandoned in the sense of being broken; English pluralization rules do not change, and the library is stable. But it is now maintenance-mode. If your project's dependency policy requires recent commit activity, go-pluralize (which explicitly maps its versions to npm `pluralize` releases) or a Rust alternative may fit better — and your output will still match Node's.

## evo-inflector — Java's Engine, Rebuilt in 2026

evo-inflector implements Damian Conway's *Algorithmic Approach to English Pluralization*, and its README makes two claims worth repeating: roughly half a million downloads a month from Maven Central, and production use in high-profile projects including Spring and JetBrains tooling.

```java
English.plural("word")        // "words"
English.plural("foot", 2)     // "feet"
English.plural("foot", 1)     // "foot"
English.plural("NightWolf")   // "NightWolves"
```

Version **2.0** is a genuine rewrite rather than a version bump: the internals moved from repeated regex and rule-list scans to a **compiled suffix-matching engine**, the old regex engine was removed, JDK 17 became the main build target, and JMH benchmarks were added for anglicized versus classical modes. The migration benchmarks quoted in the release notes report roughly **18× higher mixed-dataset throughput, ~54× faster repeated lowercase lookups, and ~27× faster repeated mixed-case lookups** compared with the old regex engine — while keeping the public `English.plural(...)` API unchanged. That last part matters: a performance rewrite that does not break callers is the best kind.

Its README is also unusually honest about accuracy, which is the most useful paragraph in any of these five repositories. Against English Wiktionary data (345,105 single-word nouns as of 2026-03-10), evo-inflector returns correct answers for **94.6% of countable nouns** but only **8.0% of uncountable nouns**, for **67.0% overall**. The README states the reason plainly: *the algorithm cannot reliably detect uncountable words — it will pluralize them anyway.*

## go-pluralize — Rule Parity with Node

go-pluralize is a Go port of the npm `pluralize` package, and its README publishes the version mapping between the two, which is exactly what you want from a port.

```bash
go get -u github.com/gertd/go-pluralize
```

```go
import pluralize "github.com/gertd/go-pluralize"

pluralize := pluralize.NewClient()
pluralize.IsPlural("Empire")   // false
pluralize.IsSingular("Empire") // true
pluralize.Plural("Empire")     // "Empires"
pluralize.Singular("Empire")   // "Empire"
```

The `IsPlural` / `IsSingular` pair is the part JavaScript's API only exposes as `isPlural`/`isSingular` single checks — in Go you get both directions on the same client, which is convenient for validation code. The client is created once and reused; it carries the rule set and any custom rules you add, so do not construct a new one per call inside a hot path.

There is also a CLI, which is genuinely handy for checking a word without writing code:

```bash
go get -x github.com/gertd/go-pluralize/cmd/pluralize
pluralize -word Empire
pluralize -word Cactus -cmd IsPlural
```

Because the port explicitly targets npm `pluralize` **8.0.0**, a Go service and a Node frontend using these two libraries will agree on output. That is a real integration advantage over mixing rule sets across languages — and it is the kind of guarantee you should test with a fixture file of domain nouns, because "explicitly tracks version X" is a claim, not a contract.

## Rust Inflector — Pluralization Plus Case Conversion

The Rust crate does more than pluralize — it also handles the naming conventions you need when generating code or mapping schemas.

```toml
[dependencies]
Inflector = "*"
```

```rust
use inflector::Inflector;

let camel: String = "some_string".to_camel_case();
```

The trait covers snake, kebab, train, camel, sentence, class and title case, plus `ordinalize`, `deordinalize`, `demodulize`, `deconstantize`, foreign key, table case, and pluralize/singularize — as both traits and free functions on `&str` and `String`. If you are building a code generator or an ORM-ish layer in Rust, that combination removes two dependencies at once.

The caveat is activity: last push **2023-06-03**. Case conversion and English pluralization rules are stable enough that this is survivable, but it is the least recently maintained library in this comparison.

## Where Inflection Libraries Quietly Break

**1. Uncountable and mass nouns.** evo-inflector's own data puts uncountable accuracy at **8.0%** — *information*, *equipment*, *series*, *data* and *software* will get pluralized anyway. For UI strings, maintain an allow-list of uncountable terms and check it before calling any library.

**2. Zero is not always plural in the target language.** `pluralize('test', 0)` returns `"tests"` and `1 item` / `0 items` reads naturally in English. That rule does not generalize — several languages use a distinct form for zero. In programmer-facing strings this is fine; in translated product text it is a bug.

**3. English-only rules in multilingual text.** The `pluralize('蘋果', 2, true)` example shows the sane behaviour — leave what you do not understand alone — but it also shows the limit. For user-visible translations, use gettext-style catalogs or ICU MessageFormat plural rules, which select among *n* locale-specific forms. Our [JavaScript i18n libraries comparison](../2026-07-28-javascript-i18n-libraries-i18next-react-intl-formatjs-vue-i18n-comparison/) covers how the format libraries wire that up, and if you are hosting the translation layer yourself, the [self-hosted translation server comparison](../2026-04-21-libretranslate-vs-argos-translate-self-hosted-translation-server-guide-2026/) is the deployment side of the same problem.

**4. Irregulars you must register.** *child/children*, *person/people* and *mouse/mice* are usually covered; your product's vocabulary is not. `addIrregularRule` in JS, custom rules in Go, or an allow-list check elsewhere — pick one place per project and keep it there.

**5. Naming conventions and display text are different problems.** Pluralizing a class name (`Order` → `Orders`) and pluralizing a sentence for a user have different correctness criteria. Deterministic rule engines are right for the first; catalogs are right for the second. The code-generation angle is covered in our [project scaffolding comparison](../2026-06-17-self-hosted-project-scaffolding-code-generation-cookiecutter-yeoman-plop-hygen/), where naming convention handling is the difference between a template that works for any project and one that works for the author's example.

**6. Constructing the engine per call.** inflect's `engine()` and go-pluralize's `NewClient()` carry rule tables. Build once, reuse — the difference shows up in loops over thousands of records.

**7. Porting assumptions between languages.** A Go service that ports Node rules is fine; a Python service that assumes Node's exact output is not. inflect, evo-inflector and pluralize implement different rule sets and will disagree on edge cases such as *index/indexes/indices* and *matrix*. If two systems must produce identical labels, share a fixture list and assert both directions.

## FAQ

### What is the best pluralization library in 2026?

By language: **inflect** 7.5.0 for Python (nouns, verbs, adjectives, ordinals, articles), **pluralize** 8.0.0 for JavaScript, **evo-inflector 2.0** for Java (Apache-2.0, used by Spring and JetBrains tooling, roughly half a million Maven Central downloads per month), **go-pluralize** for Go, and the **Inflector** crate for Rust.

### Why does my library pluralize "information" into "informations"?

Because rule-based engines cannot reliably detect uncountable nouns. evo-inflector's own accuracy data reports correct handling for only 8.0% of uncountable nouns while scoring 94.6% on countable nouns. Keep an allow-list of uncountable terms in your application and short-circuit before calling the library.

### Should I use these libraries for translated UI text?

No. They implement English rules. User-facing text in other languages needs locale-aware plural selection — gettext catalogs, ICU plural rules, or the plural support built into i18n frameworks. Use inflection libraries for developer-facing strings, log lines, generated code identifiers and table names.

### Do pluralization libraries agree with each other?

Not always. They implement different rule sets and disagree on irregular edge cases like *index* and *matrix*. If a Go service and a Node frontend must print identical labels, use go-pluralize (which explicitly ports npm `pluralize` 8.0.0) or pin both sides with a shared fixture of expected outputs.

### Is pluralize (npm) still maintained?

It was last pushed in June 2024 and remains at 8.0.0. English pluralization rules are stable, so the library is not broken — but it is in maintenance mode rather than active development. If your policy requires recent activity, evaluate a maintained port instead, noting that your output should stay compatible.

### How do I change case conventions at the same time as pluralizing?

The Rust **Inflector** crate covers both: pluralize/singularize plus snake, kebab, train, camel, sentence, class, title, table and foreign-key case conversions, and ordinalize helpers, as traits and free functions. That is the practical pick for code generators and schema mappers.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Pluralization Libraries in 2026: inflect vs pluralize vs evo-inflector vs go-pluralize",
  "description": "Pluralization and inflection libraries compared with live 2026 data: inflect 7.5.0 for Python, pluralize 8.0.0 for JavaScript, evo-inflector 2.0 for Java, go-pluralize for Go and the Inflector crate for Rust, including uncountable-noun accuracy and locale traps.",
  "datePublished": "2026-09-26",
  "dateModified": "2026-09-26",
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
