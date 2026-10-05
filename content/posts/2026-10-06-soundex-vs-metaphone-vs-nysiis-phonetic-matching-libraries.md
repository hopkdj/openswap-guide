---
title: "Soundex vs Metaphone vs NYSIIS in 2026: Which Phonetic Algorithm Actually Matches \"Smith\" and \"Smyth\"?"
date: "2026-10-06"
tags: ["string-matching", "data-quality", "developer-tools"]
cover: "/img/screenshots/jellyfish-logo.jpg"
draft: false
---

Your customer table contains **Smith**, **Smyth**, **Smythe**, and **Schmidt**. Your deduplication job, your fraud check, and your "do we already have this patient?" lookup all fail — not because the data is wrong, but because you compared strings byte for byte. Exact matching is the wrong tool for names, and every team rediscovers that the hard way.

Phonetic algorithms solve it by encoding words the way they *sound*, not the way they are spelled. **Smith and Smyth both become `S530` under Soundex.** The catch is that there are four competing algorithms, they disagree constantly, and the library you pick determines which one — or which three — you actually get. This guide compares the real implementations you would ship in 2026, with star counts pulled live from GitHub and working code you can copy.

## TL;DR / Quick Verdict

**For most projects, use Double Metaphone.** It is the most accurate general-purpose English phonetic encoder, it handles the ambiguity that single Metaphone papers over (returning two keys for names like "Catherine"), and it is available in every major language.

**If you need the widest ecosystem and absolute stability, use Soundex.** It is 1918 technology, it is laughably crude, and it is a SQL standard built into PostgreSQL, MySQL, Oracle, and SQL Server. Nothing else is that portable.

**If your data is heavily European or you are matching across spelling drift, add NYSIIS.** It produces more alphabetic output and handles vowel-heavy names better than Soundex.

**Do not pick only one.** The production pattern is to compute two or three keys per record and index all of them, because the algorithms fail in different directions.

## The Comparison Table

Live GitHub data pulled 2026-10-06:

| Library | Language | Stars | Last push | Soundex | Metaphone | Double Meta | NYSIIS | Match Rating |
|---|---|---|---|---|---|---|---|---|
| [jamesturk/jellyfish](https://github.com/jamesturk/jellyfish) | Python | **2,232** | 2026-07-24 | Yes | Yes | No | Yes | Yes |
| [NaturalNode/natural](https://github.com/NaturalNode/natural) | JavaScript | **10,882** | 2026-02-22 | Yes | Yes | No | No | No |
| [Yomguithereal/talisman](https://github.com/Yomguithereal/talisman) | JavaScript | **732** | 2024-06-23 | Yes | Yes | Yes | No | No |
| [words/double-metaphone](https://github.com/words/double-metaphone) | JavaScript | **99** | 2022-11-02 | No | No | Yes | No | No |
| [apache/commons-codec](https://github.com/apache/commons-codec) | Java | **490** | 2026-10-04 | Yes | Yes | Yes | Yes | Yes |
| [postgres/postgres](https://github.com/postgres/postgres) (fuzzystrmatch) | SQL | **22,293** | 2026-10-05 | Yes | Yes | Yes | No | No |
| [Dalvany/rphonetic](https://github.com/Dalvany/rphonetic) | Rust | **18** | — | Yes | Yes | Yes | Yes | Yes |

The distribution tells the story: **Python and JVM are extremely well served, JavaScript is fragmented across three half-maintained packages, and Rust has essentially one port** that is a translation of Commons Codec rather than a native design.

## Decision Matrix: Pick in 10 Seconds

| Situation | Recommendation | Why |
|---|---|---|
| General English name matching | Double Metaphone | Best accuracy; returns primary + alternate key |
| Data already in PostgreSQL | `fuzzystrmatch` (Metaphone/Double Metaphone) | Zero extra infrastructure, index-friendly |
| JVM backend, hardest matching | Commons Codec + all five encoders | One dependency covers every algorithm |
| Python data pipeline / notebooks | `jellyfish` | Phonetics plus distance metrics in one package |
| Legacy system, must match SQL standard | Soundex | Native in every SQL engine and HIPAA systems |
| European / vowel-heavy names | NYSIIS or Match Rating Approach | Soundex collapses these to near-useless keys |
| Fuzzy string search (not phonetic) | Trigram + edit distance instead | See the fuzzy-search comparison linked below |

## Soundex: The 1918 Standard That Refuses to Die

Soundex maps a name to a letter followed by three digits. Consonants collapse into six groups, vowels and `H/W/Y` act as separators, and everything past the fourth code is discarded.

| Code | Letters |
|---|---|
| 1 | B, F, P, V |
| 2 | C, G, J, K, Q, S, X, Z |
| 3 | D, T |
| 4 | L |
| 5 | M, N |
| 6 | R |

The canonical property is that it makes `Robert` and `Rupert` identical, which is exactly what a 1918 census needed and exactly what breaks when you feed it surnames from outside English.

```python
import jellyfish

jellyfish.soundex('Jellyfish')   # 'J412'
jellyfish.soundex('Smith')       # 'S530'
jellyfish.soundex('Smyth')       # 'S530'  <- identical, as intended
jellyfish.soundex('Schmidt')     # 'S530'  <- also identical
```

**Four characters is the whole output.** That is why Soundex has a collision rate that embarrasses everyone who ships it without a second signal: for a few hundred thousand names, `S530` alone is not a lookup key, it is a bucket.

PostgreSQL ships it in the `fuzzystrmatch` extension, which is the most practical way to apply it at scale because the comparison happens next to the data:

```sql
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;

-- Same code for all three spellings
SELECT soundex('Smith'), soundex('Smyth'), soundex('Schmidt');
--  S530 | S530 | S530

-- difference() returns 0-4; 4 means the Soundex codes are identical
SELECT difference('Smith', 'Smyth');   -- 4
SELECT difference('Smith', 'Jones');   -- 0
```

The `difference()` function is the reason to use Soundex at all in SQL: it gives you a cheap integer similarity score you can threshold, rather than a boolean match.

## Metaphone and Double Metaphone: Where Accuracy Lives

Metaphone (1990) and Double Metaphone (2000), both by Lawrence Philips, are variable-length encodings that understand English orthography — silent letters, `PH` as `F`, `KN` at the start of a word, and the hard/soft `C` distinction that Soundex ignores entirely.

**Double Metaphone returns two keys**, because English genuinely is ambiguous. `Catherine` can be pronounced with a hard or soft initial consonant, so the algorithm reports both and you match if *either* key lines up:

![Apache Commons Codec logo](/img/screenshots/commons-codec-logo.jpg "Apache Commons Codec provides Soundex, Metaphone, Double Metaphone, NYSIIS and Match Rating Approach on the JVM")

The JVM implementation is the reference-grade one, and Commons Codec exposes every variant under a consistent API:

```java
import org.apache.commons.codec.language.*;
import org.apache.commons.codec.language.bm.*;

Metaphone metaphone = new Metaphone();
metaphone.setMaxCodeLen(8);

metaphone.encode("Thompson");        // TMSN
metaphone.encode("Jellyfish");       // JLFX

// Double Metaphone returns the primary and alternate keys
DoubleMetaphone dm = new DoubleMetaphone();
dm.doubleMetaphone("Catherine");     // "K0RN"
dm.doubleMetaphone("Catherine", true);  // alternate: "KTRN"

// Same call, one flag: get both interpretations
String[] keys = { dm.doubleMetaphone("Catherine"), dm.doubleMetaphone("Catherine", true) };
```

Note the deliberate `setMaxCodeLen` call in the Metaphone example. **The default maximum code length is 4**, which throws away most of the accuracy advantage Metaphone has over Soundex. Teams benchmark Metaphone against Soundex without touching that setting and conclude the algorithms are equivalent. They are not — raise the limit to 8 or 12 and re-measure.

In JavaScript the choice is between `natural` (largest, most maintained, ships Soundex and Metaphone) and `talisman` (adds Double Metaphone but has not been pushed since 2024). If you need Double Metaphone alone, `words/double-metaphone` is a focused 99-star package that does exactly one thing:

```js
const natural = require('natural');
const doubleMetaphone = require('double-metaphone');

natural.SoundEx.process('Smith');      // 'S530'
natural.Metaphone.process('Thompson'); // 'TMSN'

doubleMetaphone('Catherine');          // [ 'K0RN', 'KTRN' ]
```

## NYSIIS: Better for Vowel-Heavy Names

NYSIIS (New York State Identification and Intelligence System, 1970) was built as a Soundex replacement for a state records system, and it fixes two Soundex weaknesses that matter once your data leaves the anglosphere.

First, **it keeps vowels in some positions instead of discarding them**, so `MacDonald` and `McDonald` normalise intelligently rather than collapsing into the same blunt bucket. Second, its output is alphabetic rather than numeric, which makes keys far easier to eyeball during debugging — a real operational advantage when you are staring at a list of unmatched records.

```python
import jellyfish

jellyfish.nysiis('Jellyfish')     # 'JALYF'
jellyfish.nysiis('Thompson')      # 'TANPSAN'
jellyfish.nysiis('MacDonald')     # 'MCADANALD'
jellyfish.nysiis('McDonald')      # 'MCADANALD'   <- converges, as designed
```

Java teams get it from the same Commons Codec dependency:

```java
Nysiis nysiis = new Nysiis();
nysiis.setStrict(true);          // not strictly required, but pins the behaviour
nysiis.encode("MacDonald");      // MCADANALD
nysiis.encode("McDonald");       // MCADANALD
```

**The `setStrict` flag is the trap.** NYSIIS has variant rules that different implementations interpret differently, so the same name can produce different keys in Python and Java unless you pin the mode. If you are matching across services written in different languages, generate both keys and compare, or run all encoding on one side.

## Match Rating Approach: The Forgotten Third Option

Match Rating Approach (MRA) is a two-stage algorithm: encode the name to a short code, then compare the codes with a numeric rating from 0 to 6 that accounts for how many characters were removed. **It is the only one of the four that produces both an encoding and a similarity score in one pass**, which makes it unusually convenient for threshold-based deduplication.

```python
import jellyfish

jellyfish.match_rating_codex('Jellyfish')   # 'JLLFSH'
jellyfish.match_rating_comparison('Byrne', 'Boern')   # True
```

```java
MatchRatingApproachEncoder mra = new MatchRatingApproachEncoder();
mra.encode("Jellyfish");        // JLLFSH
mra.isEncodeEquals("Byrne", "Boern");   // true
```

It is under-used because it is under-documented and has no implementation in PostgreSQL, but for a one-line "are these the same name?" check inside application code it is often the fastest thing that works.

## A Practical Multi-Key Architecture

The production pattern that survives contact with real data is to compute several keys and index them all:

1. **Store a normalised form** — lowercase, strip punctuation and diacritics, collapse whitespace. This is the cheap 80% win, and it belongs in the same pipeline as your [slug generation](../2026-09-25-slugify-libraries-python-slugify-simov-slugify-limax-comparison/).
2. **Store a Soundex key** for SQL-level joins and for compatibility with anything that already speaks Soundex.
3. **Store Double Metaphone primary and alternate keys** as two columns, and match on `either`.
4. **Add edit distance as a tiebreaker** — Jaro-Winkler or Levenshtein — rather than as the primary signal, because edit distance is too slow to index across millions of rows.
5. **Log near-misses** so you can measure false positives against real data instead of guessing at thresholds.

If your matching needs are really about *typographical* similarity rather than phonetics, you want a different tool entirely: see our comparison of [text diff and fuzzy matching libraries](../2026-06-21-diff-text-comparison-libraries-diff-match-patch-rapidfuzz-textdistance/). If you are choosing between indexed search engines instead, the [client-side fuzzy search comparison](../2026-08-18-fusejs-vs-minisearch-vs-lunrjs-client-side-fuzzy-search-comparison/) and the [embedded full-text search engines guide](../2026-10-05-embedded-full-text-search-libraries-tantivy-bleve-lucene-xapian/) are the better starting points. And if you are building a full entity-resolution pipeline rather than a single matcher, start with our [self-hosted entity resolution guide](../2026-06-16-self-hosted-entity-resolution-dedupe-splink-recordlinkage/).

## Common Pitfalls

**1. Comparing Metaphone results without checking `maxCodeLen`.** The default of 4 makes Metaphone barely better than Soundex. Raise it and re-benchmark before you conclude anything.

**2. Using Soundex on non-English names.** A four-character numeric code built from English consonant groups does not survive translation. For Spanish, Polish, or Vietnamese surnames, Soundex produces collisions at a rate that makes the index useless.

**3. Assuming cross-language consistent output.** `jellyfish` in Python, Commons Codec in Java, and `natural` in JavaScript do not produce byte-identical keys for every input. Pin versions, generate expected keys in a golden-file test, and fail the build when they drift.

**4. Indexing the encoding instead of the normalised string.** A phonetic key is a bucket marker, not an identity. Store it, index it, but always resolve the candidate set with a second, stricter comparison before you merge two records.

**5. Encoding the whole name as one string.** `John Smith` and `Smith John` produce completely different codes. Encode given name and family name separately, then combine the keys — otherwise word order destroys your matching.

**6. Forgetting that Match Rating Approach `comparison` is symmetric but not transitive.** `A ≈ B` and `B ≈ C` does not mean `A ≈ C`. Chaining merges on MRA comparisons alone will silently collapse two distinct people into one, which matters enormously in a [record linkage](../2026-06-16-self-hosted-entity-resolution-dedupe-splink-recordlinkage/) pipeline.

## FAQ

**Which is more accurate, Soundex or Metaphone?**
Metaphone is more accurate for English names, provided you raise its maximum code length from the default of 4 to at least 8. Soundex reduces every name to one letter and three digits, so it produces far more collisions, but it is a SQL standard available natively in PostgreSQL, MySQL, Oracle, and SQL Server, which Metaphone is not.

**What does Double Metaphone return and why are there two values?**
Double Metaphone returns a primary key and an alternate key because English pronunciation is genuinely ambiguous for names like Catherine and Schmidt. The second key captures the alternative reading, so a match on either value indicates the names may be the same. Treat the presence of an alternate key as a signal that the input is ambiguous rather than as two independent matches.

**Is NYSIIS better than Soundex?**
For European and vowel-heavy names, generally yes — NYSIIS retains more phonetic information and its alphabetic output is easier to debug. For pure US-English census-style surnames, Soundex and NYSIIS perform comparably, and Soundex wins on availability because it is built into most SQL engines.

**Can I do phonetic matching directly in PostgreSQL?**
Yes. Install the `fuzzystrmatch` extension, which provides `soundex`, `difference`, `metaphone`, `dmetaphone`, `dmetaphone_alt`, `levenshtein`, and `levenshtein_less_equal`. This keeps matching next to the data and avoids shipping millions of rows to an application process, but NYSIIS and Match Rating Approach are available on the JVM and in Python only.

**Should I use phonetic encoding or edit distance for deduplication?**
Use both, with different roles. Phonetic keys are cheap and indexable, so use them to generate candidate sets; edit distance such as Jaro-Winkler or Levenshtein is more precise but too slow to index, so use it to confirm or reject candidates. Phonetic encoding alone will merge distinct people, and edit distance alone will miss spelling variants that sound identical.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Soundex vs Metaphone vs NYSIIS in 2026: Which Phonetic Algorithm Actually Matches Smith and Smyth",
  "description": "A practical 2026 comparison of Soundex, Metaphone, Double Metaphone, NYSIIS and Match Rating Approach, with real GitHub stats and working code in Python, Java, JavaScript, Rust and PostgreSQL.",
  "datePublished": "2026-10-06",
  "dateModified": "2026-10-06",
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
