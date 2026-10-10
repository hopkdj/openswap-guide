---
title: "Text Wrapping and Hyphenation Libraries in 2026: Rust textwrap vs Python Pyphen vs Go reflow vs Java Commons Text"
date: "2026-10-10"
tags: ["text-processing", "libraries", "cli", "unicode", "developer-tools"]
draft: false
---

Every terminal UI that renders a misaligned table, every PDF generator that overlaps a margin, and every CLI that wraps a line in the middle of an ANSI color escape sequence has the same root cause: **someone used the wrong wrapping library, or hand-rolled `text.slice(0, width)` and hoped for the best.** Wrapping looks trivial until you meet CJK characters that occupy two columns, emoji that occupy two cells plus a variation selector, German nouns that hyphenate, and escape sequences that occupy zero columns while containing nine visible bytes.

The good news is that this problem has mature, well-scoped solutions in every language — and they are *not* interchangeable. The differences that matter are Unicode width awareness, ANSI awareness, hyphenation dictionary support, and whether the algorithm is greedy first-fit or optimal-fit.

## TL;DR / Quick Verdict

- **Rust, anything from CLI output to docs.rs generation?** → **textwrap**. Version 0.16, Unicode width by default, works in `no_std` with an allocator, and supports optimal-fit wrapping for genuinely justified text.
- **Python that needs real syllables (PDF, print layout, non-English)?** → **Pyphen** for hyphenation plus the stdlib `textwrap` for plain wrapping. Do not expect stdlib `textwrap` to hyphenate — it never does.
- **Go with colorized terminal output?** → **reflow**. It is explicitly ANSI-sequence aware, so styled text wraps on visible columns rather than byte offsets.
- **Java, or a platform-wide utility class?** → **Apache Commons Text**. `WordUtils.wrap` is boring, dependency-light, and maintained in the Apache release cycle.
- **JavaScript in a browser or Node?** → **hyphen** for dictionary hyphenation. There is no ANSI dimension problem in a browser, so a plain wrapper is usually enough.

**The single most common mistake:** using a byte-length or code-point-length wrapper on text that contains escape sequences or wide characters. It works in your tests (ASCII, unstyled) and breaks in production (colored, localized).

## Comparison Table

| Feature | textwrap (Rust) | Pyphen (Python) | reflow (Go) | Commons Text (Java) | hyphen (JS) |
|---|---|---|---|---|---|
| Language | Rust | Python | Go | Java | JavaScript |
| Stars | **527** | 230 | **787** | 378 | 237 |
| Last push | 2026-10-01 | 2026-09-02 | 2024-04-18 | 2026-10-10 | 2026-04-24 |
| Unicode width aware | Yes (default) | Calls separate width libs | Yes (`go-runewidth`) | Partial | Calls separate width libs |
| ANSI escape aware | Yes (feature) | No | **Yes (core)** | No | n/a |
| Hyphenation | Optional feature | **Primary purpose** | No | No | **Primary purpose** |
| Dictionary source | Optional | LibreOffice Hunspell | n/a | n/a | Hunspell-style |
| Optimal-fit / justification | `wrap_optimal_fit` | No (greedy) | No (greedy) | Greedy | Greedy |
| `no_std` support | Yes (with alloc) | n/a | n/a | n/a | n/a |
| License | MIT | GPL-2.0+/LGPL-2.1+/MPL-1.1 | MIT | Apache-2.0 | MIT |

Star counts and last-push dates were retrieved live from the GitHub API. Note the outlier: **reflow has the highest star count (787) but has not been pushed to since April 2024** — it is stable rather than abandoned, and its API has not needed to change because ANSI escape handling has not changed either.

## Scenario Decision Matrix

| Your situation | Pick | Reason |
|---|---|---|
| Rendering colored CLI tables | **reflow** | ANSI-aware wrapping is a core feature, not a plugin |
| Building a PDF from German or Dutch text | **Pyphen** | Ships LibreOffice Hunspell dictionaries with correct break points |
| Rust tool with a 64 KB flash budget | **textwrap** (`no_std`) | Works with an allocator only, disable the Unicode feature to shrink |
| Java service formatting log messages for a web view | **Commons Text** | `WordUtils.wrap` plus Apache release cadence |
| Justified text where every line ends flush | **textwrap**, `wrap_optimal_fit` | Greedy wrapping cannot produce true justification |
| Browser-side articles in multiple languages | **hyphen** | Dictionary hyphenation, no native dependency |
| Preventing overflow in a long word | Any — but set `break_words` | Without it, a 60-character token overflows every column |
| Mixed CJK and Latin text | **textwrap** or **reflow** | Both consume East Asian width tables |

## textwrap — Rust's Best-In-Class Wrapper

`mgeisler/textwrap` (527 stars, last push 2026-10-01) is the reference implementation for this problem in Rust. Add it:

```toml
[dependencies]
textwrap = "0.16"
```

By default you get **word wrapping with Unicode string support**. Those are separable Cargo features precisely so you can strip them: disable the Unicode feature to shed the width tables, or enable `unicode-width` explicitly on embedded targets where you still need accurate double-width handling.

```rust
use textwrap::{fill, wrap, Options};

fn main() {
    let text = "textwrap: a small library for wrapping text.";

    // Greedy first-fit wrapping at 18 columns.
    println!("{}", fill(text, 18));

    // Inspect the lines, or reuse a pre-built Options struct.
    let opts = Options::new(18).break_words(true);
    for line in wrap(text, opts) {
        println!("[{:>2}] {}", line.len(), line);
    }
}
```

Two behaviours are worth calling out. First, `fill()` is greedy: it fits as many words as possible per line. Second, **`wrap_optimal_fit`** solves the same problem with a cost function that penalises ragged right edges, which is what you want when you are generating justified text or typesetting rather than printing to a terminal. Greedy wrapping physically cannot produce flush-right output — no post-processing will fix it.

`break_words(true)` is the option that saves you in production: it splits tokens longer than the target width (URLs, hashes, base64 blobs) instead of letting them overflow. Terminal output containing a 128-character commit hash is the classic case.

## Pyphen — Real Hyphenation With LibreOffice Dictionaries

`Kozea/Pyphen` (230 stars, last push 2026-09-02) does one job: **hyphenate text using existing Hunspell hyphenation dictionaries**, many of which ship inside the package and come from the LibreOffice dictionary repository.

```bash
pip install pyphen
```

```python
import pyphen

dic = pyphen.Pyphen(lang='en_US')
print(dic.inserted('hyphenation'))   # 'hy-phen-ation'
print(dic.wrap('hyphenation', 5))    # [('', 'hy-'), ('phen-', 'ation')]
```

The key insight is that hyphenation is **language-specific data, not an algorithm**. Where a word may break depends on pronunciation and orthography rules that dictionaries encode. That is why Pyphen is not an alternative to `textwrap` in Rust or `WordUtils` in Java — it is a different capability layered on top. A wrapper decides *where to put the newline*; a hyphenator supplies *the legal break points* that make narrower wrapping possible.

One practical warning: Pyphen's *code* is triple-licensed (GPL-2.0+, LGPL-2.1+, MPL-1.1), and the bundled dictionaries carry GPL/LGPL/MPL terms from LibreOffice. **Check the license terms before bundling non-English dictionaries into a proprietary product.** The Python standard library's `textwrap` module has no such concern because it performs no hyphenation at all.

## reflow — ANSI-Aware Wrapping for Go

`muesli/reflow` (787 stars, last push 2024-04-18) describes itself precisely: *a collection of ANSI-sequence aware text reflow operations and algorithms*. That sentence contains the entire reason to pick it over a naive wrapper.

```go
import (
    "fmt"
    "github.com/muesli/reflow/wordwrap"
)

func main() {
    s := wordwrap.String("Hello World!", 5)
    fmt.Println(s)
    // Hello
    // World!
}
```

Because reflow understands escape sequences, `"\x1b[31m" + text + "\x1b[0m"` wraps based on the *visible* columns rather than the byte count. If you have ever seen colored text wrap three characters early, or witnessed an escape sequence get split so the rest of the terminal turns red, this is the library that prevents it. The sibling packages (`wrap`, `indent`, `padding`, `truncate`, `dedent`) share the same ANSI-aware foundation, which makes it a coherent toolkit rather than a single function.

The trade-off is purely cosmetic: reflow does not attempt optimal-fit justification, and it has no hyphenation. For interactive terminal applications — the primary consumer of Go TUI frameworks — greedy wrapping is the correct choice anyway, because a human resizing a window does not want a reflow solver's opinion.

## Apache Commons Text — The Java Baseline

`apache/commons-text` (378 stars, last push 2026-10-10, same-day activity) is a broad text utility library, and the relevant piece is `WordUtils`.

```java
import org.apache.commons.text.WordUtils;

String wrapped = WordUtils.wrap(longText, 40, "\n", true);
longText.lines().forEach(System.out::println);
```

The last argument matters: `true` means wrap *long words*, matching textwrap's `break_words`. Commons Text also brings `StringSubstitutor` for `${var}` interpolation and a set of similarity and escaping utilities, so if you are already in the Apache ecosystem you get wrapping without adding a dependency you would not otherwise want. It is deliberately boring — which, for a formatting utility embedded in a long-lived Java service, is a virtue.

## Pitfalls That Actually Bite

**ANSI sequences inflate every width calculation.** A colored string's `len()` is not its visible width. In Go use reflow; in Rust enable the ANSI feature of textwrap; in every other language strip escapes before measuring, or expect early wraps.

**Double-width characters break manual padding.** CJK ideographs, and many emoji, occupy two terminal cells. A wrapper that counts code points will under-measure and overflow. This is exactly the class of bug covered in our [terminal text width library comparison](../2026-09-27-terminal-text-width-libraries-wcwidth-uniseg-runewidth-unicode-width-comparison/), where `wcwidth`, `uniseg`, and `runewidth` each solve the measurement half of the problem.

**Combining marks and variation selectors occupy zero cells.** Accented characters assembled from a base plus a combining mark are two code points and one visible glyph. Counting code points over-estimates; counting grapheme clusters is correct.

**Greedy wrapping cannot justify text.** If your output must have flush left *and* right edges — print layout, generated PDFs, e-books — you need an optimal-fit solver, not a greedy one plus whitespace stretching.

**Hyphenation dictionaries have licenses.** A permissively licensed hyphenator with GPL dictionaries is not a permissively licensed deployment story. Verify the dictionary source, not just the code.

**Test with the ugly inputs.** Long unbroken tokens, mixed scripts, embedded escape sequences, and zero-width joiners. ASCII test fixtures give false confidence for all six pitfalls above.

## Why This Is Worth Getting Right

Text wrapping is unglamorous infrastructure, and that is precisely why the costs hide. A misaligned table in a CLI tool looks like a cosmetic bug until it makes column output unparseable for a script. A truncated error message hides the one useful word. A PDF that overlaps its margin gets rejected by a print pipeline. Choosing among these libraries is a ten-minute decision that prevents a category of production defects you would otherwise never fully eliminate.

For adjacent text-processing decisions, see our [slugify library comparison](../2026-09-25-slugify-libraries-python-slugify-simov-slugify-limax-comparison/) if you are normalising headings into URLs, our [i18n library comparison](../2026-07-28-javascript-i18n-libraries-i18next-react-intl-formatjs-vue-i18n-comparison/) if you are wrapping *localized* strings, and our [human-readable formatting libraries guide](../2026-10-06-human-readable-formatting-libraries-go-humanize-timeago-python-humanize-humantime/) for the presentation layer that usually sits next to wrapping — byte sizes, relative timestamps, and pluralisation.

## FAQ

**What is the difference between wrapping and hyphenation?**
Wrapping chooses where to break a line using spaces and existing break opportunities. Hyphenation *creates* new break opportunities inside words, based on language-specific dictionaries. Wrapping is algorithmic; hyphenation is data-driven. You generally want wrapping always, and hyphenation only when the target width is narrow relative to the language's typical word length.

**Which library handles CJK and emoji widths correctly?**
textwrap (Rust) handles East Asian width by default, and reflow (Go) consumes runewidth tables for the same purpose. In Python and JavaScript you should pair your wrapper with an explicit width measurement library rather than assuming code-point length equals display width.

**Does Python's standard library textwrap do hyphenation?**
No — never. It wraps on whitespace and, optionally, breaks long words with `break_long_words`. For syllabic breaks you need Pyphen or an equivalent dictionary-backed hyphenator.

**Why does my colored terminal output wrap too early?**
Because escape sequences are being counted as visible characters. Use an ANSI-aware wrapper such as reflow, or enable the ANSI feature in Rust's textwrap. Stripping escapes before measuring also works, but then you must re-assemble them consistently across the wrapped lines.

**Is reflow abandoned because its last commit was in 2024?**
It is best described as feature-complete rather than abandoned. The problem it solves — ANSI-aware reflow — is defined by terminal escape semantics that have not changed, and the library remains the most widely used Go option for this task, with the highest star count in this comparison.

**Can I use optimal-fit wrapping for justified text in other languages?**
The algorithm is language-independent, but hyphenation is not. For flush-right output in German, Dutch, or French, combine an optimal-fit solver with a dictionary hyphenator so it has legal break points to work with.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Text Wrapping and Hyphenation Libraries in 2026: Rust textwrap vs Python Pyphen vs Go reflow vs Java Commons Text",
  "description": "Practical 2026 comparison of text wrapping and hyphenation libraries: Rust textwrap, Python Pyphen, Go reflow, Apache Commons Text and hyphen for JavaScript, with Unicode and ANSI pitfalls.",
  "datePublished": "2026-10-10",
  "dateModified": "2026-10-10",
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
