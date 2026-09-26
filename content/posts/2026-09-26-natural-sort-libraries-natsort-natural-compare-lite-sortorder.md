---
title: "Natural Sort Libraries in 2026: natsort vs natural-compare-lite vs sortorder"
date: "2026-09-26"
tags: ["sorting", "developer-libraries", "developer-tools", "python", "javascript", "go", "cli"]
draft: false
description: "Live 2026 comparison of natural sort libraries: natsort 8.4.0 (Python), natural-compare-lite 1.4.1 (JavaScript), sortorder (Go) and natural-orderby 5.0.0. Real install commands, API samples, and the locale and version-string traps."
---

## The Bug Every CLI Ships at Least Once

Point a file listing at a directory of screenshots and you get `img1.png, img10.png, img12.png, img2.png` — the order a machine likes and no human accepts. Lexicographic comparison walks strings character by character, so `"10"` sorts before `"2"` because `'1' < '2'`. Every file browser, gallery, log viewer and backup tool eventually gets a bug report about it.

The fix is a natural sort (also called human sort): compare digit runs as numbers, and everything else as text. It sounds like a twenty-line weekend patch, and every mainstream language has at least three implementations that claim to be exactly that patch. They are not equivalent. Some compare bytes, some pull entire Unicode tables into your binary, some return wrong answers until a locale is set correctly, and at least one of the popular JavaScript options has not been touched since 2021.

This comparison covers four implementations that still receive commits in 2026: **natsort** (Python, 1,012★, last push 2026-09-19), **natural-compare-lite** (JavaScript, 113★, 2026-09-02), **sortorder** (Go, 32★, 2026-09-01) and **natural-orderby** (TypeScript, 67★, 2025-12-22). All star counts, dates and versions below were pulled live from GitHub, PyPI and npm.

**TL;DR — Quick Verdict:** In Python, install **natsort** — nothing else comes close on feature depth (filenames, locale, real numbers, precomputed keys). In JavaScript, take **natural-compare-lite**: 1.4.1, MIT, no dependencies, `a.sort(String.naturalCompare)` and you are done. In Go, **sortorder** is the right default for ASCII-leaning data, and its `casefolded` sub-package when you need case-insensitive Unicode order. For multi-key, multi-direction sorting in TypeScript, **natural-orderby** is the only one of the four that models sort *orders* as an array next to its identifiers.

## The Four Contenders at a Glance

| Library | Language | Stars | Last push | Latest release | Install | License |
|---|---|---|---|---|---|---|
| natsort | Python | 1,012 | 2026-09-19 | 8.4.0 (PyPI) | `pip install natsort` | MIT |
| natural-compare-lite | JavaScript | 113 | 2026-09-02 | 1.4.1 (npm) | `npm i natural-compare-lite` | MIT |
| sortorder | Go | 32 | 2026-09-01 | module (go get) | `go get github.com/fvbommel/sortorder` | MIT |
| natural-orderby | TypeScript | 67 | 2025-12-22 | 5.0.0 (npm) | `npm i natural-orderby` | MIT |
| javascript-natural-sort | JavaScript | 133 | 2021-10-19 | stale | *avoid for new code* | MIT |

The last row is included on purpose. **javascript-natural-sort has more stars than three of the four libraries above, and it is dead.** Stars measure history, not maintenance — check `pushedAt` before you add a dependency whose entire job is correctness of ordering.

## Decision Matrix: Pick in Ten Seconds

| Your situation | Pick | Why |
|---|---|---|
| Python script, filenames, mixed numbers | **natsort** | `natsorted()` is a drop-in for `sorted()`, handles filenames, floats and dates |
| Python, must match the OS file manager order | **natsort** (`os_sorted`) | Built specifically to mirror Explorer/Finder/GNOME ordering |
| Python, non-English collation | **natsort** (`humansorted`) | Locale-aware, with `PyICU` as an optional accelerator |
| Browser or Node, minimal footprint | **natural-compare-lite** | Single small file, no dependencies, MIT |
| Node, case-insensitive filenames | **natural-compare-lite** + `toLowerCase` wrapper | Explicit is better than an implicit locale |
| Go, ASCII filenames | **sortorder** | Tiny, no Unicode tables unless you ask for them |
| Go, case-insensitive Unicode | **sortorder/casefolded** | Unicode folding in a separate package so you opt in to the size cost |
| TypeScript, sorting records by several fields | **natural-orderby** | `orderBy(users, [v => v.name], ['asc'])` mirrors lodash's API |
| Sorting version strings (semver) | none of these | Use a semver-aware comparator; natural sort is not version sort |

## natsort — The Reference Implementation for Python

natsort 8.4.0 is not a single function, it is a small toolkit, and that is why it wins the Python slot.

```bash
pip install natsort
```

```python
from natsort import natsorted

files = ["img1.png", "img10.png", "img12.png", "img2.png"]
natsorted(files)
# ['img1.png', 'img2.png', 'img10.png', 'img12.png']
```

The README is explicit that `natsorted()` is designed as a drop-in replacement for the built-in `sorted()`: like `sorted()`, it returns a **new** list and leaves the input untouched. If you write `natsorted(files)` and then inspect `files`, nothing has changed — a genuine source of "the sort is not working" bug reports.

When the goal is to match what a desktop file manager shows, use the dedicated entry point:

```python
from natsort import os_sorted
print(os_sorted(os.listdir()))
```

`os_sorted()` handles the platform-specific details that plain `natsorted()` ignores, which is why it is the correct call for anything that lists a directory.

Locale-aware ordering is a separate function, and it comes with a real environmental caveat:

```python
import locale
from natsort import humansorted

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
humansorted(["Apple", "apple", "Banana"])
```

`humansorted()` respects locale settings such as thousands separators and case rules. Installing `PyICU` improves consistency; without it, natsort falls back to Python's built-in `locale` module, which means results can differ between machines with different system locales. The README advises reading the optional-dependencies section *before* shipping `humansorted()` anywhere user-facing.

Algorithm flags can be combined into a single call — this is the part people miss:

```python
from natsort import natsorted, ns

natsorted(files, alg=ns.REAL | ns.LOCALE | ns.IGNORECASE)
```

`ns.REAL` treats a leading `+`/`-` as part of a number (`"a-1.5"` sorts numerically against `"a1.5"`), `ns.LOCALE` enables locale collation, and `ns.IGNORECASE` collapses case differences. `realsorted()` and `humansorted()` are just shortcuts for common flag combinations, and the README notes that `humansorted(a, alg=ns.R | ns.IC)` is equivalent to `natsorted(a, alg=ns.REAL | ns.LOCALE | ns.IGNORECASE)`.

## natural-compare-lite — One File for Node and the Browser

natural-compare-lite 1.4.1 does one thing and ships no dependencies. The README states the intention plainly: compare strings containing a mix of letters and numbers the way a human would.

```bash
npm install natural-compare-lite
```

```javascript
var naturalCompare = require("natural-compare-lite")

var a = ["z1.doc", "z10.doc", "z17.doc", "z2.doc", "z23.doc", "z3.doc"];
a.sort(String.naturalCompare);
// ["z1.doc", "z2.doc", "z3.doc", "z10.doc", "z17.doc", "z23.doc"]
```

The same file works in the browser: load `natural-compare.js` with a plain script tag and `String.naturalCompare` becomes available as a comparator.

Case handling is deliberately left to you, and the documented pattern is a wrapper rather than a flag:

```javascript
a.sort(function (x, y) {
  return String.naturalCompare(x.toLowerCase(), y.toLowerCase());
});
```

That is a feature, not a gap. Node's `localeCompare()` with `numeric: true` can do natural ordering too, but its result depends on the ICU build your runtime was compiled with — which is why small CLIs and bundlers keep reaching for a deterministic comparator they can ship and test. Notably, `natural-compare-lite` is a *lite* fork: the original package grew extra options, while this one stayed small enough to inline.

## sortorder — Go's Smallest Honest Dependency

Go's standard `sort` package gives you the machinery; `sortorder` gives you the comparison functions. The module exposes `NaturalLess(str1, str2 string) bool` and `NaturalCompare(str1, str2 string) int`, plus a `Natural` type that implements `sort.Interface`.

```bash
go get github.com/fvbommel/sortorder
```

```go
import (
	"sort"

	"github.com/fvbommel/sortorder"
)

files := []string{"img1.png", "img10.png", "img2.png"}
sort.Slice(files, func(i, j int) bool {
	return sortorder.NaturalLess(files[i], files[j])
})

// or, with the ready-made sort.Interface:
sort.Sort(sortorder.Natural(files))
```

The design decision worth knowing about is the split between the root package and `casefolded`:

```go
import "github.com/fvbommel/sortorder/casefolded"

sort.Sort(casefolded.Natural(files))
```

The README explains the reason directly: case-insensitive sort orders live in a sub-package *because it pulls in the Unicode tables from the standard library, which can add significantly to the size of binaries*. If you only sort ASCII-ish filenames, the root package keeps your binary small; when you need Unicode-aware case folding, you pay for it explicitly. That is the kind of granularity a 32-star module can afford and a 5,000-star framework usually cannot.

## natural-orderby — Multi-Key Natural Ordering for TypeScript

natural-orderby 5.0.0 takes a different approach: instead of a comparator you can only apply to one field, it models the whole sort request.

```bash
npm install natural-orderby --save
```

```typescript
import { orderBy } from 'natural-orderby';

const sortedUsers = orderBy(
  users,
  [v => v.surname, v => v.firstName],
  ['asc', 'desc'],
);
```

`orderBy()` accepts a list of identifiers and a matching list of orders, natural-sorts each key, and always returns a **new** array — the README calls this out explicitly, which matters if you were relying on in-place mutation. For simple arrays the default is enough:

```javascript
orderBy(['10', 9, 2, '1', '4']);
// [ '1', 2, '4', 9, '10' ]
```

It also exports `compare()`, which can be handed straight to `Array.prototype.sort()` when you do not need per-key directions. If your existing code already uses lodash's `orderBy`, the migration is mostly an import change plus attention to how natural ordering treats numeric strings.

## Where Natural Sorting Quietly Breaks

**1. Locale-aware sorting is opt-in and machine-dependent.** `humansorted()` without `PyICU` leans on the process locale. Two servers with different `LC_ALL` values will disagree on the same input, and your test suite will only catch it on one of them.

**2. `natsorted()` does not mutate.** It mirrors `sorted()`. Assign the result: `files = natsorted(files)`.

**3. Leading zeros and chunk boundaries differ between libraries.** `"001"` versus `"1"`, or `"v1.0"` versus `"v1.0.0"`, are not covered by a single portable rule. Natural comparison defines numeric runs; it does not define your domain. Write a test with real filenames from production before trusting any of the four.

**4. Version strings are not natural sort.** `"1.9"` before `"1.10"` happens to work, but pre-release markers (`-rc1`, `+build.7`) and build metadata need semver rules. Reach for a semver comparator instead of bending a natural comparator with custom splitting.

**5. Per-comparison parsing costs real CPU.** Every comparison re-parses digit runs, so sorting a large collection does `O(n log n)` parses. In Python, precompute once with a key function and let the built-in sort do the rest:

```python
from natsort import natsort_keygen

key = natsort_keygen()
sorted(rows, key=lambda row: key(row["filename"]))
```

That converts the cost from per-comparison to per-item.

**6. Stale options are still recommended in tutorials.** javascript-natural-sort (133★) last received a push in October 2021. More stars, no maintenance — do not add it to new work.

**7. Cross-language portability is not guaranteed.** natural-compare-lite, sortorder and natsort do not implement byte-identical algorithms. If a Go service and a browser client must agree on ordering, you need a shared fixture file of filenames and an expected order, tested on both sides. That single test catches more regressions than any README reading.

## Why Bother, and Where This Fits

Natural sort is one of those libraries you never think about until it is wrong. For tooling that lists files — directory browsers, backup catalogs, media libraries, log viewers — it is the difference between a product that feels native and one that feels broken. Sorting itself has an even deeper design space: if you are choosing an algorithm for large in-memory datasets, our comparison of [modern sorting algorithm libraries](../2026-06-19-sorting-algorithm-libraries-pdqsort-quadsort-ips4o-glidesort/) covers the quicksort-family implementations where the constant factor actually matters. If your ordering problem is about how names are built rather than how they are compared, the same discipline applies to [slug generation libraries](../2026-09-25-slugify-libraries-python-slugify-simov-slugify-limax-comparison/), where Unicode normalization quietly decides whether two URLs collide.

And if you are building the listing UI itself, [modern ls replacements](../2026-06-17-self-hosted-modern-ls-replacements-eza-lsd-colorls/) show how several popular terminal tools chose their default ordering — including where they disagree with each other.

## FAQ

### What is the difference between alphabetical sort and natural sort?

Alphabetical (lexicographic) sort compares characters by code point, so `"10"` comes before `"2"` because `'1'` precedes `'2'`. Natural sort detects runs of digits and compares them as numbers, so `"2"` comes before `"10"`, while the surrounding text is still compared lexically.

### Does Python have natural sorting built in?

No. The standard library's `sorted()` and `list.sort()` are lexicographic. The usual choice is `natsort` (8.4.0, MIT), which provides `natsorted()`, `os_sorted()`, `humansorted()`, `realsorted()` and `natsort_keygen()`. For one-off cases you can approximate it with a `key=` function that splits digits and casts them to `int`, but you will hit leading zeros, decimals, locale and mixed case almost immediately.

### Why does natsort's humansorted() return different results on different machines?

Because it is locale-aware. Without the optional `PyICU` dependency it falls back to the process locale, so `locale.setlocale(locale.LC_ALL, ...)` and the host's available locales affect collation. Pin the locale explicitly, or run locale-insensitive sorting when results must be reproducible across hosts.

### Is natural sort the same as version sort?

No. Natural sort handles whole-number runs inside text, which makes `"1.9"` versus `"1.10"` work by accident. It does not implement semver precedence, pre-release ordering, or build metadata comparison. Use a version-aware comparator for versions and a natural comparator for filenames.

### Can I use natural sorting in a database query?

Only if the engine supports it. PostgreSQL and SQLite compare strings lexicographically by default, so you either store a derived sort key column, or sort after fetching. Sorting in the application with one of the libraries above is usually simpler and keeps the ordering rule in one place.

### How do I keep client and server ordering identical?

Write a fixture: a list of real filenames plus the expected order, and assert it in both codebases. Natural comparison implementations differ on case folding, leading zeros and Unicode normalization, so a shared fixture is the only reliable contract between a Go service and a browser client.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Natural Sort Libraries in 2026: natsort vs natural-compare-lite vs sortorder",
  "description": "Live 2026 comparison of natural sort libraries: natsort 8.4.0 for Python, natural-compare-lite 1.4.1 for JavaScript, sortorder for Go, and natural-orderby 5.0.0 for TypeScript, including locale and version-string traps.",
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
