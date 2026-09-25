---
title: "python-slugify vs slugify vs limax in 2026: Which Slug Library Won't Break Your URLs?"
date: "2026-09-25"
tags: ["slugify", "url-design", "developer-libraries", "i18n", "seo"]
draft: false
---

A slug library looks like the least risky dependency in your stack. It takes a title, returns a hyphenated string, and you forget about it. Then one day you upgrade it, or you enable the "modern algorithm" flag, or a user posts a title in Japanese — and every URL in your sitemap changes at once. Search engines see a site-wide 404, your analytics drop off a cliff, and the root cause is a one-line configuration default you never read.

I have watched this happen twice: once in a documentation migration where the Node and Python services disagreed about how to transliterate `Ø`, and once when a blog switched backends and silently rewrote 40% of its article URLs. That is why slug generation deserves an actual comparison instead of `npm install slugify` and hope.

Five libraries do the work in practice: **simov/slugify (1,744★, 12.4M weekly npm downloads)**, **python-slugify (1,625★)**, **gosimple/slug (1,334★, Go)**, **speakingurl (1,116★, 3.5M weekly)**, and **limax (608★)**. All figures pulled live on 2026-09-25.

## TL;DR — the 30-second verdict

- **Node/TypeScript, English-ish content, zero dependencies** → **slugify (simov)**. 12.4 million weekly downloads, MIT, and a `charmap.json` you can extend when a character transliterates wrong.
- **Python** → **python-slugify**, but pick your algorithm deliberately: `algorithm='modern'` and the default legacy pipeline **produce different slugs for the same input**, so a version bump can change your URLs.
- **Chinese, Japanese, Korean, Cyrillic content** → **limax** (or speakingurl for the non-CJK cases). It is the only one of the five that documents CJK romanisation as a first-class feature.
- **Go services** → **gosimple/slug** (MPL-2.0), with `MakeLang` for language-specific rules such as `&` → `and` vs `und`.
- **Do not use a bare transliteration table as your slug pipeline** — that is what `Unidecode` is for, and its own README warns about output quality outside Western languages.

## The five libraries side by side

| | **simov/slugify** | **python-slugify** | **gosimple/slug** | **speakingurl** | **limax** |
|---|---|---|---|---|---|
| **Stars** | 1,744 | 1,625 | 1,334 | 1,116 | 608 |
| **Language** | JavaScript | Python | Go | JavaScript | JavaScript |
| **License** | MIT | MIT | MPL-2.0 | BSD-3-Clause | Apache-2.0 |
| **Last push** | 2026-06-29 | 2026-09-22 | 2024-12-23 | 2024-03-15 | 2026-03-19 |
| **Release** | npm latest | PyPI 9.1.1 | module | npm latest | npm latest |
| **Weekly npm downloads** | **12,476,097** | — (PyPI) | — | **3,551,824** | 47,680 |
| **CJK romanisation** | charmap-dependent | via transliteration backend | no | partial | **yes (pinyin, romaji)** |
| **Keep Unicode slugs** | `strict` off + charmap | `allow_unicode=True` | no | `uric` option | `keepUnicode` |

## Decision matrix: pick in ten seconds

| Your situation | Pick | Why |
|---|---|---|
| English blog/API, Node runtime | **slugify (simov)** | Smallest dependency, largest adoption, extensible charmap |
| Any language, you want to keep native script in the URL | **python-slugify** with `allow_unicode=True` | Cleanest Unicode-preserving option of the five |
| Chinese/Japanese titles must become readable Latin URLs | **limax** | Documented pinyin and romaji output |
| Multi-language app with per-language word rules | **speakingurl** (`lang: 'de'`) or **gosimple/slug** (`MakeLang`) | Language-specific transliteration, not a single global table |
| Go monorepo, no cgo, single binary | **gosimple/slug** | Pure Go, MPL-2.0 |
| You need *any* ASCII fallback for legacy systems | **Unidecode** as a primitive | Lossy by design — see the caveats below |

## python-slugify: powerful, and the most dangerous default

python-slugify is the reference implementation in Python, actively maintained (pushed 2026-09-22, version 9.1.1) and the one I would pick for a content-heavy site — *if* you pin the algorithm explicitly. The current README documents two pipelines, and the difference is visible on ordinary input:

```python
from slugify import slugify

# Modern algorithm
assert slugify("C'est déjà l'été.", algorithm='modern') == 'c-est-deja-l-ete'
assert slugify('影師嗎', backend='text-unidecode', algorithm='modern') == 'ying-shi-ma'

# Keep the native script instead of transliterating
assert slugify('影師嗎', allow_unicode=True, algorithm='modern') == '影師嗎'

# Calling slugify() without algorithm uses the LEGACY pipeline (old default),
# kept unchanged for backward compatibility.
assert slugify("C'est déjà l'été.") == 'c-est-deja-l-ete'
```

The full signature is where the production-grade features live — note `max_length` together with `word_boundary`, which prevents the classic bug of truncating a slug mid-word, plus `stopwords` and `replacements` for removing filler:

```python
slugify(
    text, entities=True, decimal=True, hexadecimal=True,
    max_length=0, word_boundary=False, separator='-', save_order=False,
    stopwords=(), regex_pattern=None, lowercase=True, replacements=(),
    allow_unicode=False, *, replacement_stage='both', backend='auto',
    algorithm='legacy',
)
```

There is also a CLI, which is handy for generating slugs in shell scripts and CI:

```bash
pip install python-slugify

slugify "Hello, world!"          # hello-world
printf 'Café' | python -m slugify --stdin   # cafe
```

**The migration trap:** because `algorithm` defaults to the legacy pipeline for backward compatibility, upgrading python-slugify is safe — but adopting the modern algorithm later is a URL-changing event. Decide once, then treat the choice as part of your site's contract and add a redirect map before you flip it.

**The license nuance:** in the README's own example, CJK transliteration uses `backend='text-unidecode'`. The default backend is the `Unidecode` package, which is GPL-2.0. If you ship closed-source software, audit which backend you are compiling in — this is a real, if rarely noticed, compliance question.

## slugify (simov): the JavaScript default

With 12,476,097 weekly downloads, simov/slugify is what most Node projects already have in their dependency tree. It is MIT, dependency-free, works in browsers as `window.slugify`, and — importantly — ships its transliteration rules as data you can override rather than hard-coded logic.

```js
var slugify = require('slugify')

slugify('some string')        // some-string
slugify('some string', '_')   // some_string

slugify('some string', {
  replacement: '-',  // replace spaces with replacement character
  remove: undefined, // remove characters matching this regex
  lower: false,      // convert to lower case
  strict: false,     // strip special characters except replacement
  locale: 'vi',      // language code of the locale to use
  trim: true         // trim leading/trailing replacement chars
})
```

The extension model is the reason to prefer it over rolling your own: `charmap.json` holds every character-to-transliteration pair, and `locales.json` overrides entries per language, so a Vietnamese or Turkish-specific correction does not break English. Two practical notes from the README: `lower` defaults to **false** (a common surprise when your slugs look inconsistent), and when `remove` is a regex it must be a single global character class such as `/[*+~.()'"!:@]/g`.

## speakingurl and limax: when your content is not in Latin script

speakingurl (BSD-3-Clause) is the multi-language workhorse: `lang` accepts ISO 639-1 codes and applies language-specific transliteration, and the options go far beyond a separator swap.

```js
var getSlug = require('speakingurl')

getSlug("Schöner Titel läßt grüßen!? Bel été !")
// schoener-titel-laesst-gruessen-bel-ete

getSlug("Schöner Titel läßt grüßen!? Bel été !", { separator: '_' })
// schoener_titel_laesst_gruessen_bel_ete

getSlug("Schöner Titel läßt grüßen!? Bel été !", { uric: true })
// schoener-titel-laesst-gruessen?-bel-ete

getSlug("Schöner Titel läßt grüßen!? Bel été !", { truncate: 20 })
// schoener-titel
```

That `uric: true` behaviour is worth pausing on: it maps punctuation to RFC3986-safe characters instead of deleting it, so a `?` in a title survives as `?` rather than vanishing — which changes your slugs compared to a strict pipeline. Pick one behaviour and stay consistent across services.

limax extends speakingurl with the piece most libraries skip: Romanisation of Chinese and Japanese. Its README examples are unusually honest about the results:

```js
import slug from 'limax';

slug('i ♥ latin')            // i-love-latin
slug('Я люблю русский')       // ya-lyublyu-russkij
slug('我爱官话')              // wo3-ai4-guan1-hua4
slug('私は ひらがな が大好き')  // ha-hiragana-gaki
```

Note `wo3-ai4-guan1-hua4`: limax emits **tonal pinyin with tone numbers**, which is defensible transliteration and questionable URL design — readable to a Mandarin speaker, noise to everyone else. If you prefer pinyin without tones, you need a post-processing step. That is not a bug in limax so much as a reminder that no library can decide your URL aesthetics for you.

## Go: gosimple/slug and language-aware rules

For Go services, gosimple/slug (MPL-2.0, 1,334★) does the job with a tiny API, and its language-aware variants go beyond simple transliteration:

```go
text := slug.Make("Hellö Wörld хелло ворлд")
fmt.Println(text) // hello-world-khello-vorld

someText := slug.Make("影師")
fmt.Println(someText) // ying-shi

enText := slug.MakeLang("This & that", "en")
fmt.Println(enText) // this-and-that

deText := slug.MakeLang("Diese & Dass", "de")
fmt.Println(deText) // diese-und-dass

slug.Lowercase = false // keep uppercase characters
```

The `MakeLang` behaviour is the subtle part: `&` becomes `and` in English and `und` in German. If your application slugifies content in several languages, a single global transliteration table will produce URLs that native speakers find odd — this is the cheapest way to fix that on the Go side.

## Pitfalls that turn slugs into outages

**Never change your slug algorithm without redirects.** Slugs are part of your public URL contract. Migrating from legacy to modern, changing separators, or dropping a transliteration backend all rewrite URLs. Ship a 301 map generated from the old and new slug sets before deploying.

**Unicode normalisation is a prerequisite, not a detail.** `é` can be one code point or `e` + a combining accent. Slugify two visually identical titles with different normalisation forms and you can get two different slugs — normalise to NFC on input, always.

**Truncation must respect word boundaries.** `max_length` without `word_boundary` produces half-words and makes slugs unreadable. python-slugify exposes both flags for exactly this reason.

**Slugs are not identifiers.** Two different titles legitimately produce the same slug — "C++ vs C#" and "C vs C++" both collapse toward `c`-ish strings depending on settings. Always keep a stable numeric ID or a uniqueness suffix in the URL, and never use a slug as a primary key.

**Percent-encoding rules differ per component.** RFC3986 treats `/`, `?`, and `#` as reserved; a transliteration library that maps them to themselves (like speakingurl's `uric` mode) can produce slugs that break routing or analytics if you concatenate them into paths carelessly.

**Pinyin with tone numbers looks like noise to most readers.** If you serve an international audience, post-process CJK slugs to remove tone digits and consider keeping the native script in the URL instead (`allow_unicode=True` in python-slugify) — modern browsers and search engines handle UTF-8 URLs correctly.

## Making slug generation deterministic across services

The most common real-world failure is not picking a bad library — it is letting two services pick *different* libraries for the same content. A Python ingestion worker that slugs an article one way and a Node front-end that generates links another way produces 404s that only appear for certain characters, usually the ones nobody tests.

The fix is to make slug generation a single owned function with a golden test corpus. Keep a table of 30-50 nasty inputs — French apostrophes, German sharp s, Turkish dotted i, Cyrillic, Japanese, emoji, already-hyphenated titles, titles that are entirely punctuation — and assert the exact output in CI. Add a snapshot of your ten most-visited real URLs, so an upgrade that changes them fails the build instead of the SEO.

If your slugs end up as short links or redirect targets, the [self-hosted URL shortener comparison](../2026-05-06-shlink-vs-yourls-vs-polr-self-hosted-url-shortener-guide/) covers how the receiving services handle Unicode paths, and the [regex testing tool comparison](../2026-06-19-self-hosted-regex-testing-tools-regexr-ihateRegex-pythex-regexper/) is worth reading before you hand-write the sanitising patterns that inevitably grow around a slug pipeline. For products shipping multiple languages, pair slug rules with a real localisation workflow — our [translation management comparison](../weblate-vs-tolgee-vs-pootle-self-hosted-translation-management-2026/) and the [JavaScript i18n library comparison](../2026-07-28-javascript-i18n-libraries-i18next-react-intl-formatjs-vue-i18n-comparison/) cover the surrounding machinery.

## FAQ

**Which slug library changes URLs when I upgrade it?**
python-slugify is the one to watch: `algorithm` defaults to the legacy pipeline, and adopting `algorithm='modern'` produces different output for the same input. Pin the algorithm in code and add tests before upgrading.

**Can I keep non-Latin characters in URLs instead of transliterating?**
Yes. python-slugify's `allow_unicode=True` keeps the native script, and modern browsers plus major search engines handle UTF-8 URLs correctly. The trade-off is readability when links are shared outside the language community.

**Why do Chinese titles turn into pinyin with numbers?**
limax emits tonal pinyin such as `wo3-ai4-guan1-hua4`. It is linguistically precise and visually noisy; strip tone digits in post-processing if you want cleaner slugs.

**Is Japanese transliteration reliable enough for production URLs?**
It is stable, which matters more than beauty. limax documents romaji output for common cases; verify against your own content corpus before trusting it broadly, since kanji readings are context-dependent.

**What is the safest dependency for a polyglot team?**
Standardise on one library per language and one shared specification for the pipeline: normalisation form, separator, lower-casing, stopwords, maximum length, and uniqueness strategy. The specification — not the library — is what keeps URLs stable.

**Do these libraries handle emoji and symbols?**
They strip or transliterate them according to their character map. simov/slugify removes undefined symbols by default (so `unicode ♥ is ☢` becomes `unicode-love-is`), and you can extend the map for symbols you care about.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "python-slugify vs slugify vs limax in 2026: Which Slug Library Won't Break Your URLs?",
  "description": "Comparison of five open-source slug generation libraries across Python, JavaScript and Go, covering transliteration, CJK romanisation, licenses and the migration traps that rewrite your URLs.",
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
