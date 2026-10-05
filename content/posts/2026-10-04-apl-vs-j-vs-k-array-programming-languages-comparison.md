---
title: "APL vs J vs K in 2026: The Array Languages Still Powering Quant Finance"
date: "2026-10-04"
tags: ["apl", "j-language", "k-language", "array-programming", "quant", "data-analysis"]
draft: false
cover: "/img/screenshots/kona-logo.jpg"
description: "GNU APL 2.0, J9.7 and K (Kona) compared for 2026: real install commands, working array code, keyboard and licensing traps, and why trading desks still run on this notation."
---

Three programming languages, one underlying idea, and roughly sixty years of continuous use: **APL**, **J** and **K** all descend from Ken Iverson's notation for array programming, and all three still run production workloads today — most visibly on trading desks, where K's commercial descendant handles enormous volumes of time-series data. They are also the most misunderstood languages you can install in 2026: dismissed as "write-only" curiosities by people who have never seen a one-line moving average.

The three implementations worth your time today are **GNU APL 2.0** (the free ISO-standard interpreter), **J9.7** (Iverson and Hui's ASCII-only successor, released April 2026 with a 9.8 beta already available), and **Kona** (the open-source K implementation). Here is how they differ, what they actually look like, and where each one is the wrong tool.

## TL;DR — Quick Verdict

**Choose GNU APL** if you want the standard language, a free GPL interpreter, and you are willing to install an APL keyboard layout or a font mapping. **Choose J** if you want the same array-thinking power without the special characters — J uses plain ASCII digraphs, which makes it far easier to write in a normal editor and to review in a normal diff. **Choose K (Kona)** if you are specifically interested in K's terse dialect and its finance lineage, and you accept that Kona's last upstream commit was in 2023. If you want the array paradigm inside a mainstream ecosystem, be honest with yourself: you may be better served by NumPy-style vectorisation in Python, because the ecosystem cost of these three is real.

## At-a-Glance Comparison

| | GNU APL 2.0 | J9.7 | K (Kona) |
|---|---|---|---|
| **Notation** | Unicode APL symbols (`⍳`, `⍴`, `÷`) | ASCII digraphs (`i.`, `$`, `%`) | ASCII terse K (`!`, `#`, `%`) |
| **Standard basis** | ISO/IEC 13751 (Extended APL) | Iverson notation, ASCII | K3-era K |
| **Latest release** | GNU APL 2.0 (full tar release) | J9.7 (April 2026) | Kona, last commit 2023-06-02 |
| **Source host** | GNU Savannah | `jsoftware/jsource` (740★) | `kevinlawler/kona` (1,416★) |
| **Licence** | GPL-3.0 | GPL-3.0 or commercial | ISC |
| **Interpreter written in** | C++ | Portable C | C |
| **Evaluation order** | Right to left | Right to left | Right to left |
| **Special keyboard needed** | Yes, or a font/keymap | **No** | No |
| **Verbs/adverbs model** | Primitive functions and operators | Primitives, forks and hooks (tacit style) | Verbs and adverbs |
| **Typical domain** | Teaching, standards work, finance, actuarial | Analytics, teaching, prototyping | Time-series, trading systems |
| **Best for** | Learning standard APL with zero licence cost | Array programming in a normal editor | Understanding the K family and its lineage |

Repository figures were read from GitHub at the time of writing; GNU APL is hosted on GNU Savannah rather than GitHub, so it has no star count to compare.

## Use-Case Decision Matrix

| Your situation | Pick | Why |
|---|---|---|
| You want to learn array programming properly | **GNU APL** | It implements the ISO standard, so what you learn transfers |
| You write code in VS Code and live in git diffs | **J** | ASCII digraphs, no special glyphs, no input method |
| You are curious about how kdb+ and K work | **Kona** | An open-source K implementation you can read and build |
| You need array operations on a mixed workload | **None of the three** | Use a mainstream language with a vectorised library |
| You want zero licence friction | **GNU APL or Kona** | GPL-3.0 and ISC respectively |
| You need commercial support and clear licensing | **J** | Dual-licensed; commercial terms exist |
| You maintain something written in APL already | Match the original | Migration is a rewrite, not a port |

## GNU APL 2.0: The Standard, Freely Implemented

GNU APL describes itself as "a free interpreter for the programming language APL" and an "(almost) complete implementation of ISO standard 13751". Version 2.0 is a full release with a tarball, a Debian package and a Windows installer — a deliberate change from the 1.9 era, when the project shipped incremental fixes through its Savannah repository instead.

Install it from the GNU FTP mirror or from your distribution:

```bash
# From source
wget https://ftp.gnu.org/gnu/apl/apl-2.0.tar.gz
tar xzf apl-2.0.tar.gz
cd apl-2.0
./configure && make && sudo make install

# Or use the distribution build
sudo apt-get install apl
```

At the interpreter, whole arrays are the unit of work. There are no loops to write:

```apl
      ⍳ 5
1 2 3 4 5

      +/ ⍳ 100
5050

      N ← 1 2 3 4
      (+/ N) ÷ ⍴ N
2.5

      2 3 ⍴ ⍳ 6
1 2 3
4 5 6
```

`⍳` generates an index vector, `+/` inserts addition between elements (a reduction), `⍴` is shape — reshaping when it appears to the left, counting when it appears to the right — and `÷` is division. Evaluation runs right to left, so `(+/)  N` is a single phrase: "sum N". That right-to-left rule is what makes APL read like algebra and, to newcomers, like line noise.

The practical friction is input. APL needs glyphs like `⍳` and `⍴` that are not on a standard keyboard; GNU APL ships a font and keymap, and most users add an input method or a compose-key layer. Plan for that before you start teaching it to a team.

## J9.7: Array Programming Without the Glyphs

J is the continuation of Iverson's work by Iverson and Roger Hui, and its central design decision is a good one: **everything is ASCII**. Where APL writes `⍳5`, J writes `i.5`. The release reported on the project's own README is **J9.7**, available since April 2026, with a **J9.8 beta** alongside it. The source lives at `jsoftware/jsource` under a dual GPL-3.0 / commercial licence.

```bash
# J ships per-platform installers; the engine is portable C
# and can also be built from the jsource repository (see overview.txt)

# On macOS, Homebrew is the shortest path to a working interpreter
brew install jlang
```

```j
   i. 5
0 1 2 3 4

   +/ i. 100
4950

   (+/ % #) 1 2 3 4
2.5
```

Note the difference from the APL example: `i.5` produces **0 1 2 3 4**, not 1 2 3 4 5, so the sum of the first hundred indices is 4950 rather than 5050. This is the kind of off-by-one that makes array code feel like a trick until it becomes obvious.

The `(+ / % #)` line is the classic J **fork**: three verbs in a row form a train, applied as "sum divided by count" — a mean in six characters, with no named argument anywhere. J's tacit style, where programs are built by composing verbs rather than mentioning data, is the deepest expression of the Iverson idea and the hardest part of the language to learn.

## K (Kona): The Terse Dialect and Its Finance Lineage

K is the third branch of the family, the direct ancestor of the commercial kdb+ time-series database that runs on many trading floors. **Kona** is the open-source implementation of K, released under the ISC licence, with 1,416 stars and a last upstream commit in **June 2023** — mature, readable, but not actively developed.

```bash
# macOS
brew install kona

# Build from source (macOS, Linux, BSD, Cygwin)
git clone https://github.com/kevinlawler/kona.git
cd kona
make          # use gmake on BSD

# Start a session
./k
```

```k
  !5
0 1 2 3 4

  +/ !100
4950

  x: 1 2 3 4
  (+/ x) % #x
2.5
```

`!` is "enumerate", `#` is count (and reshape when applied in that role), and `%` is division. K pushes terseness further than either APL or J — the language is famously small enough that its reference implementation has been described as a few pages of C. That economy is also its weakness for newcomers: there is very little redundancy in the notation to help you recover from a mistake.

Kona is the right choice for reading and building K code and for understanding where kdb+ came from. It is the wrong choice for a new production system, because upstream development stopped in 2023.

## Why These Languages Still Matter

Array programming's core claim is that **the array is the data type**, not a collection to be iterated. When you write `+/ ⍳ 100` you are not describing a loop; you are naming a value. The interpreter decides how to evaluate it. In a world where vectorised hardware (SIMD units, GPUs, columnar analytics engines) rewards exactly this style of expression, the idea is more relevant in 2026 than the syntax's age suggests.

The second reason is historical weight. The K family is embedded in financial infrastructure that will not be replaced soon, which means K-literate engineers remain employable in a very narrow, very well-paid niche. If that niche interests you, this family is the entire on-ramp.

The third reason is educational. Learning any of the three rewires how you think about iteration, reshaping and reduction — and that thinking transfers back to whatever else you write. If you enjoy this class of comparison, the same discipline of reading a language family by its implementations shows up in [Scheme implementations: Racket, Chez and Guile](../2026-09-13-scheme-implementations-racket-chez-guile-comparison/), [Forth implementations: gforth, pforth and zeptoforth](../2026-09-14-forth-implementations-gforth-pforth-zeptoforth-guide/) and [Prolog engines: SWI-Prolog, Scryer and Trealla](../2026-09-13-prolog-engines-swi-prolog-scryer-trealla-comparison/). For another take on terse, historically important runtimes with their own aesthetics, [Smalltalk web stacks](../2026-09-15-smalltalk-web-stacks-pharo-seaside-squeak-gnu-smalltalk/) is the closest analogue.

## Pitfalls Before You Commit

**1. Input and fonts.** APL needs a keyboard mapping; budget an afternoon per machine, and be aware that pasting APL into issue trackers and chat can mangle the glyphs.

**2. Readability is a team property, not a language property.** Terse array code is superb for experts and hostile to newcomers. If more than one person maintains it, add comments and keep functions small — the language will not do it for you.

**3. Ecosystem is thin.** There is no npm, no PyPI equivalent with depth, and no popular package for, say, parsing a web API. These languages solve numerical and analytical problems; everything around them is your job.

**4. Tooling gaps.** Debuggers, profilers and linters are minimal compared with mainstream languages. Expect to debug by printing arrays.

**5. Maintenance risk.** Kona's upstream has been quiet since 2023 and kdb+ is commercial. GNU APL and J are both actively released, which is the safer long-term bet — the GNU project explicitly prefers its Savannah repositories as the most supported way to track APL between releases.

**6. Don't rewrite for its own sake.** Existing APL code is a cost centre to be maintained, not a challenge to be won. Match the dialect your code already uses.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "APL vs J vs K in 2026: The Array Languages Still Powering Quant Finance",
  "description": "GNU APL 2.0, J9.7 and K (Kona) compared for 2026: install commands, working array code, keyboard and licensing traps, and where the array paradigm still wins.",
  "datePublished": "2026-10-04",
  "dateModified": "2026-10-04",
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

**What is the difference between APL, J and K?**
All three are array languages descended from Ken Iverson's notation, and all three evaluate expressions right to left with no explicit loops. APL uses Unicode glyphs and is standardised as ISO/IEC 13751. J is the ASCII-only successor, which replaces glyphs with digraphs like `i.` and `$`. K is the terse dialect that became the commercial kdb+ time-series database; Kona is the open-source implementation of it.

**Is APL still used in 2026?**
Yes, mostly in finance, insurance, actuarial work and teaching. Its continued relevance comes from the fact that array-at-a-time expression maps naturally onto vectorised and columnar hardware, and from a large body of existing code that is expensive to rewrite. GNU APL 2.0 shipped as a full release with a Debian package and a Windows installer.

**Which is easiest to learn: APL, J or K?**
J, if only because the ASCII notation removes the keyboard problem entirely — you can write and review it in a normal editor. APL is the best documented and most standardised, which matters if you want knowledge that transfers. K (Kona) is the tersest and therefore the least forgiving, but its small vocabulary is a genuine advantage once you are past the basics.

**Why do array languages evaluate right to left?**
Because the notation is designed so that meaningful phrases stay contiguous. Reading right to left lets you write `(+/N) ÷ ⍴N` — "sum of N, divided by the count of N" — as one consistently parsed expression without layers of parentheses. The cost is that most programmers must consciously override the precedence rules they learned elsewhere.

**Can I run APL or J in Docker?**
Yes, both can be containerised, and GNU APL's build is a conventional `./configure && make` so a multi-stage image is straightforward. J is distributed as portable C with per-platform installers and can be built from source. Neither has an official Docker Hub image to pull, so plan to build your own.

**Is Kona a replacement for kdb+?**
No. Kona is an open-source implementation of the K language under the ISC licence and is excellent for learning the dialect and reading K code. kdb+ is a commercial product with a database engine, tooling and support contracts. Kona's last upstream commit was in 2023, so treat it as a stable reference implementation rather than a platform to build a business on.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
