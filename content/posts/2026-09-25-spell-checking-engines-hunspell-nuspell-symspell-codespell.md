---
title: "Hunspell vs SymSpell vs Nuspell in 2026: Which Spell Checking Engine Should You Self-Host?"
date: "2026-09-25"
tags: ["spell-checking", "text-processing", "developer-libraries", "search", "self-hosted"]
draft: false
cover: "/img/screenshots/nuspell-cli.jpg"
---

Here is the uncomfortable truth about spell checking in production software: almost every product uses the same thirty-year-old C++ library, almost nobody understands it, and the moment you need suggestions in a search box, a typo-tolerant API, or a multilingual form, the library you already depend on is the wrong shape for the job.

Spell checking is not one problem — it is three. **Human-facing dictionaries** (is this word valid in Brazilian Portuguese?), **fuzzy lookup** (did the user mean "Kubernetes" when they typed "kubernets"?), and **content linting** (does the repo contain "langauge" in a code comment?). The four serious open-source engines solve different ones: **Hunspell (2,594★)**, **Nuspell (274★)**, **SymSpell (3,467★)**, and the lint-focused pair **codespell (2,427★)** and **misspell (1,405★)**.

All figures below were pulled live from GitHub, PyPI, and NuGet on 2026-09-25. Every command is copied from the projects' own documentation.

## TL;DR — the 30-second verdict

- **Shipping a desktop or web app with real dictionaries for 100+ languages and Hunspell `.aff`/`.dic` compatibility** → **Hunspell**. It is what LibreOffice, Firefox, and Chrome ship, it is LGPL-2.1, and it was pushed on 2026-09-24.
- **Same dictionaries, modern C++ codebase, and you want more speed** → **Nuspell**. LGPL-3.0, ICU-backed Unicode, and documented as *up to 3.5× faster than Hunspell*.
- **Typo tolerance inside search, autocomplete, or an API** → **SymSpell**. It is not a dictionary checker; it is a symmetric-delete fuzzy index that corrects ~5,000 words per second per core.
- **Catching typos in a codebase or docs in CI** → **codespell** (Python, actively maintained) or **misspell** (Go, but no push since 2024-06-12).

**Pick one dictionary engine (Hunspell or Nuspell) and one fuzzy engine (SymSpell). They are complementary, not competitors.**

## The five engines compared

| | **Hunspell** | **Nuspell** | **SymSpell** | **codespell** | **misspell** |
|---|---|---|---|---|---|
| **Stars** | 2,594 | 274 | 3,467 | 2,427 | 1,405 |
| **Last push** | 2026-09-24 | 2026-09-11 | 2026-07-04 | 2026-09-23 | 2024-06-12 |
| **Language** | C++ | C++17 | C# | Python | Go |
| **License** | LGPL-2.1 | LGPL-3.0 | MIT | GPL-2.0 | MIT |
| **Index format** | `.aff` + `.dic` | `.aff` + `.dic` (compatible) | frequency dictionary + bigrams | curated typo pairs | curated typo pairs |
| **Core algorithm** | MySpell affix stripping | Affix stripping + ICU | Symmetric Delete | dictionary matching | dictionary matching |
| **Latest release** | 1.7.x | tracked on the site | **6.7.3** (NuGet) | **2.4.3** (PyPI) | last tag 2023-era |
| **Best for** | Language coverage | Speed, Unicode, safety | Fuzzy correction at scale | CI spell lint | Go codebases |

## Decision matrix: pick in ten seconds

| Your situation | Pick | Why |
|---|---|---|
| Text editor / office suite needs 100+ languages | **Hunspell** | Largest dictionary ecosystem in existence |
| Same dictionaries but you want modern code and ICU casing rules | **Nuspell** | `.aff`/`.dic` compatible, faster, safer APIs |
| Search box: "did you mean…" for a query with two typos | **SymSpell** | Sub-millisecond lookup, no language dictionary needed |
| Compound splitting: "thequickbrownfox" → 53 words | **SymSpell WordSegmentation** | Linear-time segmentation with correction |
| CI gate that fails on "recieve" in comments | **codespell** | Actively maintained, trivially scriptable |
| Tiny dependency in a Go build | **misspell** | Single binary, but factor in the 2024 staleness |

## Hunspell: the engine you are already using

Hunspell is the descendant of MySpell and Ispell, maintained by its original author, and it powers the spell checker in LibreOffice, Firefox, Chrome, and most Linux distributions. It is a library (C++/C APIs), a command-line tool, an Ispell-pipe-compatible filter, and it has bindings for most languages.

The critical thing to understand is that Hunspell is **two files, not a word list**: an `.aff` rules file that describes morphology and affixation, and a `.dic` dictionary of stems. That design is why it handles agglutinative languages such as Turkish, Finnish, and Hungarian, where a naive word list would need millions of entries.

Where to get the dictionaries matters legally. The README points at the LibreOffice dictionary files, which carry their own licenses (LGPL/MPL/GPL depending on the language) — audit them before shipping a commercial product:

```bash
# Debian/Ubuntu
sudo apt install hunspell hunspell-en-us

# Dictionary files (LibreOffice upstream, pinned revisions from the Hunspell README)
wget -O en_US.aff https://cgit.freedesktop.org/libreoffice/dictionaries/plain/en/en_US.aff?id=a4473e06b56bfe35187e302754f6baaa8d75e54f
wget -O en_US.dic https://cgit.freedesktop.org/libreoffice/dictionaries/plain/en/en_US.dic?id=a4473e06b56bfe35187e302754f6baaa8d75e54f
```

The CLI is genuinely useful for debugging a dictionary before you integrate the library. Note the single-character result codes: `*` means a valid dictionary stem, `+` a valid affixed form, `&` a misspelling with suggestions, and `#` a misspelling without any:

```bash
# Spell-check a file, reporting bad words with suggestions
hunspell -d en_US text.txt

# Pipe mode: read from stdin, print only misspelled words
hunspell -d en_GB -l < text.txt

# Interactive session — type words, get verdicts
$ hunspell -d en_US
example
*
teached
& teached 9 0: taught, teased, reached, teaches, teacher, leached, beached

# Stemming and morphological analysis
hunspell -d en_US -s    # mice -> mouse
hunspell -d en_US -m    # mice  st:mouse ts:Ns
```

That `-m` output is the feature people forget Hunspell has: it is also a morphological analyser, which is why language-learning tools and search normalisers use it rather than a plain spell checker.

## Nuspell: a modern rewrite with the same dictionaries

Nuspell exists because Hunspell's codebase shows its age. It is written in modern C++17, requires ICU4C for Unicode casing (Turkish dotted/dotless i, German sharp s), and — per its own README — claims *up to 3.5 times faster* checking than Hunspell while remaining **backward compatible with the Hunspell dictionary format**. That compatibility is the headline: your `.aff` and `.dic` files keep working, so migration is a library swap, not a dictionary migration.

![Nuspell-powered spell checking with suggestions in a document editor](/img/screenshots/nuspell-cli.jpg "Nuspell's suggestion quality in a real editor: ranked alternatives with affix-aware candidates")

Build it from source on Ubuntu or Debian; the dependency list is short because ICU is the only runtime dependency:

```bash
sudo apt install g++ cmake libicu-dev catch2 pandoc doxygen

mkdir build && cd build
cmake ..
make -j
sudo make install
sudo ldconfig   # sometimes needed on Linux
```

**The migration caveat that costs teams a day:** Nuspell is *dictionary*-compatible, not ABI-compatible with `libhunspell`. If your application links `libhunspell.so` directly (through a language binding that expects Hunspell's C API), you cannot drop Nuspell in as a shared library — you either use Nuspell's own API or expose it over a process boundary. For an application you control, porting the API calls is usually an afternoon; for a stack of third-party plugins that assume Hunspell symbols, it is a project.

## SymSpell: the fuzzy correction engine

SymSpell solves the other half of the problem. It is not a dictionary checker and it does not know what a "correct" word is in the linguistic sense — it knows what a **frequent** word is, and it finds the closest frequent word to any input in sub-millisecond time. The trick is the Symmetric Delete algorithm: instead of generating all transposes, replaces, and inserts for an input term, it precomputes deletes for dictionary terms, so an average five-letter word needs only **25 deletes** to cover roughly **3 million** possible errors within edit distance 3.

Published performance from the project itself: **0.2 ms per word at edit distance 2, ~5,000 words/second on a single core of a 2012 laptop**. The current NuGet package is **6.7.3**, and the library targets .NET Standard 2.0, so it runs on .NET Framework, .NET Core (including Linux), and Xamarin.

```bash
dotnet add package SymSpell --version 6.7.3
```

```csharp
// Create the index: capacity, then max edit distance for dictionary precalculation
int initialCapacity = 82765;
int maxEditDistanceDictionary = 2;
var symSpell = new SymSpell(initialCapacity, maxEditDistanceDictionary);

// Load the 82,765-term frequency dictionary shipped with the project
symSpell.LoadDictionary("frequency_dictionary_en_82_765.txt", termIndex: 0, countIndex: 1);

// Single-word correction
var suggestions = symSpell.Lookup("house", SymSpell.Verbosity.Closest, maxEditDistanceLookup: 1);
foreach (var s in suggestions)
    Console.WriteLine($"{s.term} {s.distance} {s.count:N0}");

// Multi-word correction WITH compound splitting and merging (needs the bigram dictionary)
symSpell.LoadBigramDictionary("frequency_bigramdictionary_en_243_342.txt", termIndex: 0, countIndex: 2);
var fixedText = symSpell.LookupCompound("whereis th elove hehad dated", maxEditDistanceLookup: 2);

// Segmentation of text with missing spaces — linear time, unlike dynamic programming
var segmented = symSpell.WordSegmentation("thequickbrownfoxjumpsoverthelazydog");
Console.WriteLine(segmented.correctedString);
```

`WordSegmentation` deserves more attention than it gets. It splits strings with missing spaces (OCR output, line-break damage, hashtags, camelCase identifiers) in **O(n)** time using a triangular matrix instead of recursion, correcting misspellings as it goes. If you have ever written a regex to split a corrupted OCR line, this replaces it.

**Two memory facts you must plan for.** First, the precalculated dictionary is the point of the algorithm, so memory scales with dictionary size and edit distance — the README explicitly notes that enabling the "Prefer 32-bit" compiler option significantly reduces memory consumption for the .NET version. Second, for compound correction you need the bigram dictionary in addition to the unigram one; without it, `LookupCompound` has nothing to score word pairs with.

## codespell and misspell: lint your repositories, not your prose

These two are frequently mistaken for spell checkers in the dictionary sense. They are not. Both ship a curated list of common typos (`recieve` → `receive`) and scan files, which makes them ideal CI gates and useless for validating user input.

```bash
# codespell — Python 3.9+, current release 2.4.3
pip install codespell
codespell                    # dry run over the current directory
codespell -w -i 3            # write fixes, interactive
codespell -L nd,ba,iff .     # allow project-specific words
codespell -S "*.min.js,*.svg" docs/ src/
```

```bash
# misspell — Go, single static binary
go install github.com/client9/misspell/cmd/misspell@latest
misspell all.html your.txt important.md
misspell -w your.txt                  # rewrite in place, only if a typo is found
misspell -locale US important.txt     # narrow to a locale (US vs UK)
```

The choice between them is mostly about your toolchain: codespell is actively maintained (pushed 2026-09-23, version 2.4.3) and has an ignore-word workflow that survives large monorepos, while misspell is a beautifully small Go binary whose last push was 2024-06-12. For a Go-only repository, misspell is fine. For everything else in 2026, codespell is the safer default.

**False positives are the real operational cost.** Both tools flag identifiers, abbreviations, and domain vocabulary, so budget a first pass to populate an ignore list — otherwise your team learns to ignore the CI job, which is worse than not having it.

## Pitfalls that bite in production

**Dictionary licenses are not the same as engine licenses.** Hunspell is LGPL-2.1 and Nuspell is LGPL-3.0, but the dictionaries are separate works with their own terms. Shipping a commercial product with LibreOffice dictionaries without auditing per-language licenses is a legal risk, not a technical one.

**Edit distance is a memory budget, not a quality dial.** Raising `maxEditDistanceDictionary` in SymSpell increases precalculation memory superlinearly. Anyone who has set it to 4 "to be safe" has met the out-of-memory exception.

**Hunspell's suggestion quality depends entirely on the affix file.** Two `.dic` files with the same words but different `.aff` rules produce noticeably different suggestions — the affix rules are what make "teached" suggest "taught" instead of nothing.

**Do not run a dictionary engine per request.** Hunspell and Nuspell load dictionaries into memory; initialising one per HTTP request is a latency disaster. Load once at process start or use a long-lived worker.

**Unicode casing needs special-case rules, not `toLowerCase()`.** Turkish `İ`/`ı` and German `ß` break naive case folding. This is exactly why Nuspell depends on ICU rather than hand-rolled normalisation — worth the extra dependency if you serve non-English users.

**Nuspell and Hunspell will disagree on edge cases.** They aim for dictionary compatibility, not bug-for-bug behavioural equivalence. If your tests assert exact suggestion ordering, expect diffs after a library swap.

## Where spell checking fits in your stack

Spell checking is usually one component in a text pipeline, not the product. If your correction layer feeds a search index, the tokenisation and stemming settings in your search engine matter more than the dictionary: our [full-text search engine comparison](../2026-05-17-self-hosted-fulltext-search-sphinx-manticore-solr-guide/) covers how analysers and stemming interact, and if you are correcting queries client-side instead of server-side, the [client-side fuzzy search comparison](../2026-08-18-fusejs-vs-minisearch-vs-lunrjs-client-side-fuzzy-search-comparison/) covers the JavaScript options.

For teams shipping multilingual products, dictionary availability is a release-blocking constraint — check language coverage before you standardise on an engine, and see how it fits the wider localisation workflow in our [self-hosted translation management comparison](../weblate-vs-tolgee-vs-pootle-self-hosted-translation-management-2026/). If your product renders localised UI strings, the [JavaScript i18n library comparison](../2026-07-28-javascript-i18n-libraries-i18next-react-intl-formatjs-vue-i18n-comparison/) is the natural companion read on the message-catalogue side.

## FAQ

**Is Nuspell a drop-in replacement for Hunspell?**
At the dictionary level, yes — it reads the same `.aff` and `.dic` files. At the API and ABI level, no. Applications linking `libhunspell` need code changes or an adapter process.

**Can SymSpell be used instead of a dictionary spell checker?**
Only if "correct" means "frequent for this corpus". SymSpell has no notion of grammar or valid morphology, so it will happily suggest a frequent word when the input was a legitimate rare one.

**Which engine handles compound words like German or Dutch best?**
Hunspell and Nuspell, because compound handling is encoded in the affix file and both implement it. SymSpell's `LookupCompound` and `WordSegmentation` handle missing spaces and merged words, which is a different problem.

**Do I need a GPU or a large server for any of this?**
No. All five tools run on a single CPU core with modest memory. SymSpell's dictionary precalculation is the only step that grows with configuration, and it happens once at startup.

**What is the smallest useful deployment?**
codespell in CI plus SymSpell in your query path covers most products: one catches typos in what you write, the other fixes what users type. Add Hunspell or Nuspell only when you need to validate words in 50+ languages.

**Are these tools subject to the same breaking changes as language models in their suggestions?**
No — suggestions come from deterministic dictionary and edit-distance lookups. The same input and dictionary version always produce the same ranking, which makes regression testing straightforward.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Hunspell vs SymSpell vs Nuspell in 2026: Which Spell Checking Engine Should You Self-Host?",
  "description": "Practical comparison of open-source spell checking engines: Hunspell, Nuspell, SymSpell, codespell and misspell, with live star counts, licenses, install commands and real CLI examples.",
  "datePublished": "2026-09-25",
  "dateModified": "2026-09-25",
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
