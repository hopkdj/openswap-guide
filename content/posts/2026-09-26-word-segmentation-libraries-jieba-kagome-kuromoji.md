---
title: "Jieba vs Kagome vs Kuromoji in 2026: Which Word Segmenter Should You Actually Deploy?"
date: "2026-09-26"
tags: ["text-processing", "tokenization", "developer-libraries", "i18n", "self-hosted"]
draft: false
---

Paste `南京市长江大桥` into any system that splits on spaces and you get exactly one token: a meaningless eleven-character blob. Chinese, Japanese and Thai do not put spaces between words, so before a search index, a log pipeline, a content filter or a keyword extractor can do anything useful with them, some component has to decide where the word boundaries are. That component is a **word segmenter**, and the wrong one quietly poisons everything downstream — broken search recall, useless word clouds, and keyword rules that never fire.

The good news is that the serious open-source options are small, self-containable, and free of vendor lock-in: **Jieba** for Chinese, **Kagome** for Japanese, **Kuromoji** for JVM shops, plus **WordNinja** and **wordfreq** for the English and statistical side of the same problem. Between them they cover the four questions you actually have to answer — Chinese, Japanese, "the text has no spaces at all", and "I need frequency data, not splitting".

## TL;DR — the 30-second verdict

- **Chinese text, Python stack, custom vocabulary** → **Jieba 0.42.1**. 35,169 stars, MIT, three segmentation modes, and user dictionaries that override the built-in dictionaries per domain.
- **Japanese text, Go service, no cgo** → **Kagome v2.11.0**. Pure Go, MIT, actively pushed (2026-09-19), and it ships both a CLI and a tokenize server mode.
- **Japanese inside an existing JVM or Lucene application** → **Kuromoji**. Apache-2.0, self-contained IPADIC build, but frozen since January 2023 — treat it as a legacy integration, not a new project.
- **English strings that lost their spaces** (`thequickbrownfox`, `#emergencyservicenotice`) → **WordNinja 2.0.0**. One function, no service, probabilistic split based on word frequencies.
- **You need frequency ranks rather than segmentation** → **wordfreq 3.1.1**. Apache-2.0 tables covering dozens of languages.

If you are building something new in 2026 and only reading one line of this article: **Kagome for Japanese, Jieba for Chinese, and never segment with `text.split()` again.**

## The comparison table (data pulled 2026-09-26)

| Project | Language | Latest release | GitHub stars | Last commit | Licence | Segmentation approach |
|---|---|---|---|---|---|---|
| **Jieba** | Python | PyPI **0.42.1** | 35,169 | 2024-08-21 | MIT | Prefix-dictionary DAG + HMM for unknown words |
| **Kagome** | Go | **v2.11.0** | 983 | 2026-09-19 | MIT | MeCab-compatible morphological analyzer, dictionary bundled |
| **Kuromoji** | Java | **0.9.0** (Maven) | 1,059 | 2023-01-23 | Apache-2.0 | IPADIC-based morphological analyzer, self-contained jar |
| **WordNinja** | Python | PyPI **2.0.0** | 875 | 2023-02-19 | MIT | Word-frequency dynamic programming split |
| **wordfreq** | Python | PyPI **3.1.1** | 1,751 | 2025-01-04 | Apache-2.0 | Frequency tables (not a segmenter) |

Two things stand out. Kagome is the only project in the Japanese column that has been touched this month, and Jieba — despite a last release in 2024 — remains the most-starred segmenter in the world by a factor of thirty. Star count is not maintenance, but it does mean the answer to "how do I do this in Python for Chinese?" has been settled for years.

## Which one for which job

| Use case | Pick | Why |
|---|---|---|
| Chinese search index, keyword extraction, content moderation | **Jieba** | Search mode produces overlapping tokens that match more queries; user dictionaries fix domain terms without retraining |
| Chinese + Traditional Chinese mixed corpus | **Jieba** (with an explicit dictionary) | Dictionary switching is a one-line call, so one process can serve both scripts |
| Japanese product text in a Go microservice | **Kagome** | Single static binary, no cgo, no dictionary download at runtime |
| Japanese tokenization as an internal HTTP API | **Kagome server mode** | Keeps the analyzer out of your application binary entirely |
| Japanese inside Lucene, Elasticsearch or a JVM monolith | **Kuromoji** | Already in the dependency graph; a rewrite buys little |
| Splitting run-together English or identifiers | **WordNinja** | Purpose-built for exactly this, one dependency |
| Ranking, autocomplete, "is this even a word" checks | **wordfreq** | Prebuilt Zipf frequencies for dozens of languages |
| Mixed CJK + Latin documents | **Jieba + Kagome** | Segment each script with a native analyzer, then join the token streams |

## Jieba: the Chinese default that still earns its 35,169 stars

Installation is deliberately boring:

```bash
pip install jieba
```

Jieba exposes three segmentation modes, and the difference between them is the single most useful thing to understand before you wire it into a search path.

```python
import jieba

# Precise mode - no overlapping tokens, best for indexing text once
print("/".join(jieba.cut("南京市长江大桥")))

# Full mode - every word a character could belong to, best for recall experiments
print("/".join(jieba.cut("南京市长江大桥", cut_all=True)))

# Search-engine mode - re-cuts long words into shorter ones so partial
# queries still match. This is the one most people actually want.
print("/".join(jieba.cut_for_search("南京市长江大桥")))
```

Search mode is worth the extra tokens: it splits `长江大桥` into `长江` + `大桥` as well, so a query for `大桥` still hits a document that contains the full compound. If your users type short queries — and they do — this is the difference between a search feature that works and one that returns nothing.

### Custom dictionaries are the real feature

Out-of-the-box dictionaries will mangle product names, internal codenames and new idioms. Jieba's fix is a plain text file, one entry per line, `word frequency part-of-speech`, in UTF-8:

```text
云原生网关 5 n
数据湖仓 5 n
运维大屏 3 n
```

```python
import jieba

jieba.load_userdict("userdict.txt")

# Term frequency matters: give a domain term a high frequency if it must win
# against a competing split of the same characters.
jieba.add_word("数据湖仓", freq=20000)
```

Two operational notes that save real debugging time. First, Jieba builds an in-memory trie on first use, so call `jieba.initialize()` during application start-up rather than inside the first request handler. Second, the module-level functions all delegate to one global tokenizer object (`jieba.dt`), so if you need two different dictionaries in one process, create explicit tokenizers instead of mutating the global one:

```python
from jieba import Tokenizer

zh_news = Tokenizer(dictionary="dict_news.txt")
zh_support = Tokenizer(dictionary="dict_support.txt")
print("/".join(zh_support.cut("客户工单自动分派")))
```

Jieba also ships part-of-speech tagging (`jieba.posseg`) and can run multi-process segmentation with `jieba.enable_parallel(4)` — useful when you are backfilling an index over millions of documents and a single core is the bottleneck. There is an optional sequence-labelling mode that swaps in a separate model package; the README pins it to `paddlepaddle-tiny==1.6.1`, so treat it as a pinned experiment rather than a default upgrade path. For most workloads the dictionary DAG plus the unknown-word model is accurate enough, and the plain install stays dependency-free.

## Kagome: Japanese tokenization as a single Go binary

Kagome is what you reach for when the answer must be a binary, not a service account. It is pure Go — no cgo, no external dictionary files to download at runtime — and the repository was pushed on 2026-09-19, which makes it the only actively maintained general-purpose Japanese analyzer in this comparison.

```bash
go get -u github.com/ikawaha/kagome/v2/...
```

The library API is small enough to quote from the project's own README:

```go
package main

import (
	"fmt"
	"strings"

	"github.com/ikawaha/kagome/v2/tokenizer"
)

func main() {
	t := tokenizer.New()
	tokens := t.Tokenize("寿司が食べたい。")
	for _, token := range tokens {
		if token.Class == tokenizer.DUMMY {
			// BOS: Begin Of Sentence, EOS: End Of Sentence.
			fmt.Printf("%s\n", token.Surface)
			continue
		}
		features := strings.Join(token.Features(), ",")
		fmt.Printf("%s\t%v\n", token.Surface, features)
	}
}
```

For batch work the CLI is the faster path. Kagome's CLI advertises the same three modes Japanese analyzers have converged on — `normal`, `search` and `extended`:

```bash
# tokenize a file, splitting compounds so partial queries match
kagome tokenize -mode search -file input.txt
```

`normal` splits conservatively (longest reasonable units), `search` splits compounds further for retrieval, and `extended` goes furthest — useful for analysis, too noisy for indexing. Choose once per index and keep it consistent: mixing modes inside one index produces token streams that cannot be compared.

Kagome also exposes a `server` sub-command that runs a tokenize server, which is the cleanest deployment shape if your application is not written in Go: run the analyzer as a sidecar, keep your stack unchanged, and you can pin the analyzer version independently of the application. If you would rather not run a sidecar at all, the library is only a handful of lines, so a 30-line HTTP wrapper around `tokenizer.New()` is a legitimate option — and that wrapper is the only code you own.

## Kuromoji: still fine, still frozen

Atilika's Kuromoji (1,059 stars, Apache-2.0) remains the path of least resistance inside a JVM. It is self-contained — the IPADIC dictionary ships inside the artifact, so there is nothing to download at runtime — and it exposes the same normal / search / extended mode distinction. If you already have Lucene, Elasticsearch or a Spring application, and you only need Japanese tokenization to feed it, Kuromoji costs you one dependency:

```xml
<dependency>
    <groupId>com.atilika.kuromoji</groupId>
    <artifactId>kuromoji-ipadic</artifactId>
    <version>0.9.0</version>
</dependency>
```

Be clear-eyed about the trade-off: the repository's last commit was **2023-01-23**. That does not make it broken — dictionaries and morphological rules change slowly — but it does mean nobody is fixing edge cases, and new Japanese vocabulary (product names, slang, loanwords) will not appear in the built-in dictionary until you supply a user dictionary yourself. Kuromoji is a perfectly good answer to "I already run Java"; it is a poor answer to "which Japanese analyzer should I adopt in 2026".

## WordNinja: splitting English text that lost its spaces

Not every segmentation problem is Asian. Hashtags, usernames, scraped identifiers and legacy exports arrive as run-together English: `#emergencyservicenotice`, `redteamtraining`, `thequickbrownfox`. WordNinja (875 stars, MIT, PyPI **2.0.0**) solves exactly that with a word-frequency-driven dynamic-programming split:

```bash
pip install wordninja
```

```python
import wordninja

print(wordninja.split("thequickbrownfox"))
# ['the', 'quick', 'brown', 'fox']

print(wordninja.split("emergencyservicenotice"))
# ['emergency', 'service', 'notice']
```

The project is a repackaging of a well-known competitive-programming answer, which is exactly why it is fast and small — and also why it has limits. It is English-only, it has no notion of grammar, and it will happily split a meaningless token into two plausible English words. Use it to normalise noisy identifiers before search, not to reverse-engineer words you care about. Last commit 2023-02-19, so pin the version you test with.

## Wordfreq: the frequency table you probably need

Sometimes you do not want to split text at all — you want to know how common a word is, so you can rank candidate splits, weight autocomplete, or filter garbage. **wordfreq** (1,751 stars, Apache-2.0, PyPI **3.1.1**) ships Zipf-scale frequencies for dozens of languages:

```bash
pip install wordfreq
```

```python
from wordfreq import zipf_frequency, word_frequency

# Zipf scale: roughly 1 (rare) to 8 (extremely common)
print(zipf_frequency("gateway", "en"))
print(zipf_frequency("kubernetes", "en"))

# Raw per-token probability, if you are doing maths rather than thresholds
print(word_frequency("gateway", "en"))
```

One caveat matters more than the API: the README states the tables are **a snapshot of language usage through about 2021**, and that the maintainer does not currently intend to refresh them. That is a fair trade for a stable, dependency-free lookup table, but it means post-2021 vocabulary will score as rare or unknown. Train your thresholds accordingly, and treat frequency as one signal rather than the truth.

## Pitfalls that only show up in production

- **Segmenter output is a versioned interface.** Upgrade Jieba, change a mode, or add a dictionary and your token stream changes — which invalidates every index built with the old configuration. Record the segmenter version, mode and dictionary hash alongside the index, and plan to re-segment when any of them change.
- **Warm up before serving.** Both Jieba and Kagome load dictionaries at start-up. Calling the first segmentation inside a request handler turns your first user into a load test. Initialise at boot.
- **Normalise before segmenting, not after.** Full-width digits and Latin letters (`１２３`, `ＡＢＣ`), half-width katakana, and mixed-case Latin all change the dictionary lookup result. Fold them to a canonical form first, or the same sentence will segment differently depending on where it came from.
- **Never segment URLs, emails, file paths or code identifiers.** Segmenters assume natural language. Run those tokens through a pre-pass that extracts and masks them, then restore afterwards.
- **Do not mix modes inside one index.** Search mode's overlapping tokens compared against normal mode's tokens is a recall bug that looks like a relevance bug.
- **Beware the English-only trap.** WordNinja on Chinese returns confident nonsense, and Jieba on Japanese produces garbage tokens. Route by Unicode script before you route by model.
- **Frequency thresholds need a reference corpus.** Absolute Zipf cut-offs tuned on one corpus rarely transfer; validate on your own data before shipping a filter.

## Deploying a segmenter as a service

The pragmatic architecture for a multi-language pipeline is one small analyzer per script family rather than one clever polyglot service:

1. **Detect script** per document (a Unicode range check is enough for CJK-vs-Latin routing; you do not need a classifier).
2. **Route** Chinese to Jieba, Japanese to Kagome, and the remaining Latin runs to WordNinja.
3. **Cache aggressively.** Segmentation is deterministic given version + mode + dictionary, so a small LRU cache on normalised text removes most of the cost in support and search workloads where the same strings repeat.
4. **Pin and record.** Container image tag, mode, dictionary file hash. That tuple is the contract between your index and your analyzer.

For Japanese specifically, Kagome's server mode plus a read-only container image is the least-moving-parts deployment in this comparison: one binary, static dictionary, no network access required at runtime.

## Why self-host your text processing?

Text is where the sensitive data lives. Support tickets, chat logs, document uploads and search queries are exactly the payloads you least want to ship to a third-party endpoint, and segmentation is the first step of every pipeline that touches them. Running the analyzer yourself keeps the raw text inside your network, removes per-request pricing and rate limits from your capacity plan, and lets you pin behaviour for years instead of accepting whatever the vendor's model serves this week.

It also composes well with the rest of a self-hosted stack. If you are already normalising text encodings, our [Unicode encoding libraries guide](../2026-06-20-unicode-encoding-libraries-icu4c-simdutf-encoding-rs-uchardet/) covers the layer beneath this one — the codecs and normalisation that decide what bytes your segmenter ever sees. If your pipeline touches emoji-heavy user content, the [emoji processing libraries comparison](../2026-06-21-emoji-processing-libraries-twemoji-gemoji-noto-emojilib/) covers the grapheme handling that segmentation alone will not give you. And if the end goal is an offline reference or translation tool, our [self-hosted CLI dictionary and translation tools article](../2026-06-17-self-hosted-cli-dictionary-translation-translate-shell-sdcv-dictd/) shows what a locally hosted lexical pipeline looks like in practice.

## FAQ

**Which segmenter should I use for Chinese in 2026?**
Jieba. It has the largest ecosystem by a wide margin (35,169 stars), an MIT licence, three segmentation modes and a user-dictionary mechanism that handles domain vocabulary without code changes. Its inactivity since 2024 is a maintenance risk rather than an accuracy problem, and the dictionaries are stable.

**Is Kuromoji still usable, given the last commit was in 2023?**
Yes, and it remains the right choice if your application is JVM-based and already carries the artifact. Be aware that you will maintain new vocabulary yourself, and that no upstream fixes are coming.

**Why would I use Kagome instead of Kuromoji for Japanese?**
Because it is actively maintained and because it deploys as a static Go binary with the dictionary compiled in. It also offers a tokenize server mode, so a Python or Ruby application can consume it over HTTP without taking on a Go build.

**Do I need a heavy server or GPU to run any of this?**
No. Every tool in this comparison is a CPU-only library or command-line program. Throughput scales by running more processes or container replicas over batches of documents, not by buying accelerators.

**Can I combine several segmenters in one pipeline?**
Yes, and for mixed-script corpora you should. Detect the script per text run, route Chinese to Jieba and Japanese to Kagome, then merge the token streams. Keep the mode and dictionary of each analyzer pinned so the merged output stays reproducible.

**What is the most common mistake with word segmentation?**
Treating `split()` as a fallback for non-Latin text. A space-based split on Chinese or Japanese returns entire sentences as single tokens, which silently destroys recall without raising a single error.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Jieba vs Kagome vs Kuromoji in 2026: Which Word Segmenter Should You Actually Deploy?",
  "description": "Hands-on comparison of open-source word segmentation libraries in 2026: Jieba, Kagome, Kuromoji, WordNinja and wordfreq, with real versions, star counts and deployment guidance.",
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
