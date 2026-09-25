---
title: "Humanize vs Pretty-Bytes vs Filesize in 2026: Stop Formatting Bytes by Hand"
date: "2026-09-26"
tags: ["developer-libraries", "text-processing", "cli-tools", "i18n", "observability"]
draft: false
---

Open any log file and you will find it: `8589934592 bytes`, `timeout_ms: 3600000`, `usage: 0.30000000000000004`. Storing raw values is correct — you should never persist "8.0 GB" as your source of truth — but somewhere between the database and the human, every one of those numbers has to become readable. That translation is where teams quietly accumulate a `formatBytes()` helper with three off-by-one bugs, a hardcoded `1000`, and a `KB` label that is wrong for half its callers.

The libraries that solve this properly are small, boring, and unusually well maintained. **go-humanize**, **python-humanize**, **pretty-bytes**, **filesize.js** and **HumanizeDuration.js** cover byte sizes, durations, ordinals, plurals and relative timestamps across Go, Python and the browser — and four of the five were pushed within the last three weeks. Here is what each one actually does, and where the standard `1024 vs 1000` traps are hiding.

## TL;DR — the 30-second verdict

- **Go service** → **go-humanize** (4,830 stars, MIT). `humanize.Bytes` for SI, `humanize.IBytes` for binary, plus `Time`, `Comma`, `Ordinal`, `Ftoa`, `SI` and an English-language subpackage.
- **Python application or CLI** → **python-humanize** (PyPI **4.16.0**, MIT). One import covers sizes, durations, ordinals, word numbers and locale-aware relative times.
- **Browser or Node code that only needs byte sizes** → **pretty-bytes** (npm **7.1.3**, **31.7M weekly downloads**). Tiny, tree-shakeable, zero dependencies.
- **Bytes with SI / IEC / JEDEC switching in one package** → **filesize.js** (npm **11.0.24**, BSD-3-Clause, 16.5M weekly downloads). The only library in this set that treats the unit *standard* as a first-class option.
- **Human-readable durations in JavaScript** → **HumanizeDuration.js** (npm **3.35.0**, **Unlicense**). `12000` becomes `"12 seconds"`, in 40+ languages, with no runtime dependencies.

If you are hand-rolling one of these formatters in 2026, you are writing a correctness bug with a friendly name.

## The comparison table (data pulled 2026-09-26)

| Library | Language | Latest version | Stars | Last push | Licence | Weekly npm downloads |
|---|---|---|---|---|---|---|
| **go-humanize** | Go | module (master) | 4,830 | 2026-09-23 | MIT | — |
| **python-humanize** | Python | PyPI **4.16.0** | 759 | 2026-09-16 | MIT | — |
| **pretty-bytes** | JS / TS | npm **7.1.3** | 1,311 | 2026-09-18 | MIT | **31,674,266** |
| **filesize.js** | JS / TS | npm **11.0.24** | 1,709 | 2026-09-25 | BSD-3-Clause | **16,523,568** |
| **HumanizeDuration.js** | JS / TS | npm **3.35.0** | 1,736 | 2026-09-11 | Unlicense | **3,123,256** |

The download counts are the interesting column. `pretty-bytes` at 31.7 million weekly installs is not a niche utility — it is infrastructure, which is a good argument for using it rather than writing your own.

## kB, KiB, KB: the standards argument you cannot skip

Before comparing code, settle the unit question, because it decides which library you need:

- **SI / decimal (base 10):** `1 kB = 1000 B`. Correct per the SI prefix system, preferred by storage vendors and network engineers. `8,589,934,592 bytes = 8.59 GB`.
- **IEC / binary (base 2):** `1 KiB = 1024 B`, with distinct prefixes (KiB, MiB, GiB) defined by IEC 80000-13. Preferred for memory and by most operating systems. `8,589,934,592 bytes = 8 GiB`.
- **JEDEC:** the legacy habit of writing `KB`/`MB` while meaning 1024. Widely used by RAM vendors and still legally required in some jurisdictions — and the reason a "1 TB" drive shows as 931 GB in your file manager.

A formatter that hardcodes one of these and labels its output with the other produces the class of bug where a dashboard and a `du` run disagree by 7%, and nobody believes either number. The practical rule: **pick the standard once per surface, make it a parameter, and never let a formatter change standard as a side effect of an upgrade.**

## Which library for which job

| Use case | Pick | Why |
|---|---|---|
| Go API returning byte sizes | **go-humanize** | `Bytes` (SI) and `IBytes` (binary) as separate functions — no ambiguity |
| Go CLI printing "3 days ago" | **go-humanize** | `humanize.Time` handles the relative-time wording |
| Python data pipeline, notebook or script | **python-humanize** | Sizes, durations, ordinals, word numbers in one import |
| Python with non-English output | **python-humanize** | Built-in locale activation for relative time and plurals |
| Frontend bundle where size matters | **pretty-bytes** | ~1 kB, no dependencies, one function |
| Configurable SI / IEC / JEDEC output | **filesize.js** | The `standard` option plus structured `output` modes |
| Duration strings in a web UI | **HumanizeDuration.js** | 40+ languages, `largest` and `units` control |

## go-humanize: one import for units, times, ordinals and words

```bash
go get github.com/dustin/go-humanize
```

Go's version is refreshingly explicit about the standards question — there are two functions, and you pick:

```go
import "github.com/dustin/go-humanize"

// SI / decimal: 82854982 -> "83 MB"
fmt.Printf("That file is %s.\n", humanize.Bytes(82854982))

// Binary: 82854982 -> "79 MiB"
fmt.Printf("That file is %s.\n", humanize.IBytes(82854982))
```

The rest of the package covers the other formatting chores you would otherwise hand-roll:

```go
fmt.Printf("This was touched %s.\n", humanize.Time(someTimeInstance))
// This was touched 7 hours ago.

fmt.Printf("You owe $%s.\n", humanize.Comma(6582491))
// You owe $6,582,491.

fmt.Printf("You are my %s best friend.\n", humanize.Ordinal(193))
// You are my 193rd best friend.

fmt.Printf("%s\n", humanize.Ftoa(2.24))   // 2.24 (trailing zeros removed)
fmt.Printf("%s\n", humanize.SI(0.00000000223, "M")) // 2.23 nM
```

There is also a small English-language subpackage that solves pluralisation and list joining without string concatenation guesswork:

```go
import "github.com/dustin/go-humanize/english"

english.Plural(1, "object", "")   // 1 object
english.Plural(42, "object", "")  // 42 objects
english.Plural(99, "locus", "loci") // 99 loci

english.WordSeries([]string{"foo", "bar", "baz"}, "and")        // foo, bar and baz
english.OxfordWordSeries([]string{"foo", "bar", "baz"}, "and")  // foo, bar, and baz
```

Two operational notes. `humanize.Bytes` defaults to the decimal interpretation, so if your file sizes come from `du`, `ls` or a filesystem API, use `IBytes` to match what the user already sees. And `humanize.Time` is intentionally fuzzy — it returns "7 hours ago", not a timestamp — so never persist its output or assert on it in tests; assert on the raw `time.Time` and let the display layer stay loose.

## python-humanize: the widest coverage of any library here

```bash
python3 -m pip install --upgrade humanize
```

Sizes first, with the standard exposed as a parameter rather than a build-time choice:

```pycon
>>> import humanize
>>> humanize.naturalsize(1_000_000)
'1.0 MB'
>>> humanize.naturalsize(1_000_000, binary=True)
'976.6 KiB'
>>> humanize.naturalsize(1_000_000, gnu=True)
'976.6K'
```

`binary=True` switches to 1024-based units with IEC suffixes; `gnu=True` keeps the 1024 maths but emits compact GNU-style labels — the exact combination you need when matching `du -h` output. Then the layer most teams forget they need, number and time formatting:

```pycon
>>> humanize.intcomma(12345)
'12,345'
>>> humanize.intword(123455913)
'123.5 million'
>>> humanize.apnumber(41)
'41'
>>> humanize.naturaltime(datetime.now() - timedelta(seconds=3600))
'an hour ago'
```

Durations get the most configurable treatment of any library in this comparison:

```pycon
>>> humanize.precisedelta(delta)
>>> humanize.precisedelta(delta, minimum_unit="microseconds")
>>> humanize.precisedelta(delta, suppress=["days"], format="%0.4f")
>>> humanize.naturaltime(delta, minimum_unit="milliseconds")
```

`precisedelta` is the answer to "how long did this build actually take" — it will print days, hours, minutes and seconds together instead of collapsing to "2 hours". And because it is a Python package, `humanize.fractional`, `humanize.scientific` and `humanize.metric` are available for the same reason `Ftoa` exists in Go: nobody should be writing their own float pretty-printer.

## pretty-bytes: the smallest correct answer in JavaScript

```bash
npm install pretty-bytes
```

```javascript
import prettyBytes from 'pretty-bytes';

prettyBytes(1337);                    // '1.34 kB'
prettyBytes(100);                     // '100 B'
prettyBytes(1337, {bits: true});      // bits instead of bytes
prettyBytes(42, {signed: true});      // explicit sign for deltas
```

Its role is narrow on purpose: bytes in, string out, and it is the default dependency for that job across the JavaScript ecosystem (31.7 million weekly downloads). Use it when all you need is decimal sizes in a UI. If you need to switch standards at runtime, or to format bits, IEC units and structured output from the same function, reach for filesize.js instead.

## filesize.js: the only one that models the unit standard

```bash
npm install filesize
```

```javascript
import { filesize, partial } from 'filesize';

filesize(1024);                        // '1.02 kB'  (SI by default)
filesize(1024, {standard: 'iec'});     // '1 KiB'
filesize(1024, {bits: true});          // '8.19 kbit'
filesize(1536, {output: 'array'});     // [1.54, 'kB']
filesize(1024, {output: 'object'});    // { value, symbol, exponent, unit }
```

The option table is where this library distinguishes itself — every knob that matters is explicit:

| Option | Default | What it controls |
|---|---|---|
| `standard` | `''` | Unit standard: `si`, `iec` or `jedec` |
| `base` | `-1` | Number base: `2`, `10`, or `-1` to auto-detect |
| `bits` | `false` | Calculate bits instead of bytes |
| `round` | `2` | Decimal places |
| `output` | `'string'` | `string`, `array`, `object` or `exponent` |
| `locale` | `''` | Locale-aware output, `true` for the system locale |
| `roundingMethod` | `'round'` | `round`, `floor` or `ceil` |

The `output: 'object'` mode is the one to know about if you are building a dashboard: you get the numeric value and the unit symbol separately, so you can style the unit differently, translate it, or compare values without ever parsing a formatted string back into a number. And `partial()` gives you a preconfigured formatter — configure the standard once, then call it everywhere, which is exactly how you stop a codebase from drifting between 1000 and 1024.

## HumanizeDuration.js: durations in 40+ languages

```bash
npm install humanize-duration
```

```javascript
const humanizeDuration = require('humanize-duration');

humanizeDuration(12000);  // '12 seconds'
humanizeDuration(3000);   // '3 seconds'
humanizeDuration(2250);   // '2.25 seconds'
```

The API is one function with an options object, and the options are the reason to use it rather than `Math.round(ms / 1000) + 's'`: `round` for whole units, `largest` to cut output at a single unit ("1 day" instead of "1 day, 3 hours, 12 minutes"), `units` to restrict which units may appear, `language` for localisation, and `delimiter` for list joining. It ships under the **Unlicense**, which places it in the public domain — convenient if your legal review treats vendored MIT code differently from public-domain code.

## Pitfalls that show up after you ship

- **Never store formatted output as the source of truth.** Keep bytes as integers everywhere and format only at the edge. A stored `"8.6 GB"` cannot be summed, compared or charted.
- **Rounding hides regressions.** At one decimal place, a 4% size increase is invisible on a dashboard. Alert on raw bytes; format only for display.
- **One standard per surface.** Do not mix SI labels in the API with IEC labels in the UI. Decide once, pass the option explicitly, and write it down.
- **Never parse your own formatted string.** If you find code doing `parseFloat(str)` on `"1.34 kB"` to get a number back, the design is inverted — return `output: 'object'` (filesize.js) or the raw integer instead.
- **Sort before you format.** Formatting first turns numeric sorting into lexicographic sorting, where `"9 MB"` outranks `"10 MB"`.
- **Do not concatenate pluralisation.** `count + " item" + (count > 1 ? "s" : "")` breaks on `locus`/`loci`, on 0, and on every language that is not English. go-humanize's `english.Plural` and python-humanize's built-ins exist for this.
- **Check the licence when vendoring.** MIT, BSD-3-Clause and Unlicense all permit bundling, but they carry different notice requirements. Automated licence checks are cheap; a legal review after a release is not.
- **Treat formatted relative time as unstable.** "an hour ago" changes between two calls a second apart. Snapshot tests on `naturaltime`, `humanize.Time` or `humanize-duration` output will flake; freeze the clock instead.

## Why keep the formatting layer in your own code

There is no service to self-host here — and that is precisely the point. Unit and duration formatting looks like a candidate for "just call an API", which is how teams end up shipping their raw byte counts, internal metrics and timestamps to a third party in order to render a number with a friendlier suffix. These libraries are tiny, offline, and version-pinnable, so the formatting layer stays inside your network with everything else.

It also composes with the rest of a self-hosted toolchain. If you are aggregating measurements from several systems, our [units of measurement libraries comparison](../2026-06-28-cpp-units-of-measurement-libraries-mp-units-nholthaus-boost-units/) covers the typed-unit layer that prevents the `1000 vs 1024` class of errors at the type level rather than in a formatter. If the values you are formatting are timestamps rather than durations, the [Python datetime libraries guide](../2026-08-10-python-datetime-libraries-arrow-pendulum-dateutil/) and the [C++ datetime libraries comparison](../2026-06-25-cpp-datetime-libraries-date-h-boost-datetime-icu-abseil-cctz/) cover the parsing and arithmetic that should happen *before* anything becomes a string.

## FAQ

**Which of these should I use in a Go service?**
go-humanize. It is the most widely used option in the Go ecosystem, actively maintained (2026-09-23), MIT licensed, and it separates SI (`Bytes`) from binary (`IBytes`) so you cannot accidentally mix standards. `Time`, `Comma`, `Ordinal` and `Ftoa` cover the neighbouring chores.

**Is 1 MB 1000 or 1024 bytes?**
By default, no — the two conventions both exist. SI uses base 10, so 1 MB is 1,000,000 bytes; IEC uses base 2, so 1 MiB is 1,048,576 bytes. The legacy JEDEC habit of writing "MB" while meaning 1024 is the source of the confusion. Choose a standard per surface and expose it as an option.

**Why does my drive's "1 TB" show up as 931 GB?**
Because the vendor advertises decimal (SI) capacity while your operating system reports binary (IEC) units under binary-labelled names. Both numbers are correct — they describe different units. filesize.js's `standard` option and python-humanize's `binary` flag let you display either one deliberately.

**Do I need a different library for durations and for byte sizes?**
Usually yes in JavaScript: pretty-bytes and filesize.js handle sizes, while HumanizeDuration.js handles durations. In Go and Python, a single library (go-humanize, python-humanize) covers both, which is one fewer dependency to track.

**Are these libraries safe to bundle into a frontend?**
Yes. pretty-bytes is roughly a kilobyte with no dependencies, filesize.js is dependency-free, and HumanizeDuration.js ships under the Unlicense. Just confirm the licence notices your build requires — MIT and BSD-3-Clause both expect attribution.

**Can I localise the output?**
python-humanize supports locale activation for relative times and plurals, filesize.js accepts a `locale` option for number and unit formatting, and HumanizeDuration.js ships dozens of language packs. If none of them covers your format, supply the unit symbols yourself via filesize.js's structured output rather than string-replacing the result.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Humanize vs Pretty-Bytes vs Filesize in 2026: Stop Formatting Bytes by Hand",
  "description": "Comparison of human-readable formatting libraries in 2026: go-humanize, python-humanize, pretty-bytes, filesize.js and HumanizeDuration.js, with real versions, download counts and SI versus IEC guidance.",
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
