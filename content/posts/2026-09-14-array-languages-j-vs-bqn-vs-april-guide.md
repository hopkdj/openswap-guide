---
title: "Array Languages in 2026: J vs BQN vs April Compared"
date: "2026-09-14"
tags: ["array-programming", "j-language", "bqn", "apl", "common-lisp", "programming-languages"]
draft: false
cover: "/img/screenshots/bqn-logo.jpg"
---

Most programming languages assume you want to write loops. Array languages assume the opposite: you want to describe the *shape* of a computation and let the interpreter do the iterating. The result is notationally dense enough to look like line noise and powerful enough to replace forty lines of numerical Python with six characters — and in 2026 there are three living, actively developed open-source options worth knowing.

**J** is the ASCII-fied descendant of APL with the deepest documentation and a mature 2026 release. **BQN** is the modern redesign: a small language with a precise specification and a fast C implementation. **April** embeds a subset of APL directly inside Common Lisp, for people who want array thinking without leaving their Lisp system.

This is a practical comparison: what each one is good at, how to install it, and the traps that eat your first weekend.

## TL;DR: Quick Verdict

**Choose J** if you want the most battle-tested array language with encyclopaedic documentation and you are fine with two-character ASCII primitives like `+/` and `*:`. **Choose BQN** if you want cleaner semantics, a readable specification, and the fastest open-source array engine available — CBQN. **Choose April** if your codebase is already Common Lisp and you want APL's expressive power as a library. If you have never used an array language before, start with **BQN**: the spec is short enough to actually read.

## The Three Contenders Side by Side

| Implementation | Language model | Repository | Stars | Last activity | Install route | Sweet spot |
|---|---|---|---|---|---|---|
| **J (J9.7)** | ASCII APL descendant, right-to-left | `jsoftware/jsource` (engine mirror) | **740** | 2026-09-14 | Official installers per platform; source builds via the repo | Mature statistics, teaching, long-lived scripts |
| **BQN / CBQN** | Modern redesign of APL, glyph-based | `mlochbaum/BQN` (spec) + `dzaima/CBQN` (engine) | **1,076** / **407** | 2026-08-27 / 2026-09-14 | `make && sudo make install`, plus distro packages | New projects, performance, embeddable array engine |
| **April (APL in Lisp)** | APL subset compiled to Common Lisp | `phantomics/april` | **661** | 2026-05-29 | Quicklisp: `(ql:quickload 'april)` | Lisp systems that need array operations |

All three are open source and all three saw commits within the last few months. The J source is dual-licensed (GPL 3 and commercial), while the 2026 J release — **J9.7**, shipped in April 2026, with a J9.8 beta already available — is distributed free of charge for every major platform including Raspberry Pi, iOS, and Android.

## Decision Matrix: Ten Seconds to a Decision

| Your situation | Pick | Reason |
|---|---|---|
| First time with array programming | **BQN** | Spec and tutorial are short, consistent, and readable in an evening |
| Heavy numerical/statistical workloads | **J** | Decades of matrix, statistical, and string primitives with a deep wiki |
| Need maximum throughput on one machine | **CBQN** | Compiles with `make o3n` to target your exact CPU |
| Embedding array ops in a C or JS program | **BQN / CBQN** | CBQN embeds cleanly; a JavaScript implementation also exists |
| Already running SBCL or CCL | **April** | Array expressions become another Lisp macro in your existing system |
| Teaching vectorised thinking | **J** | ASCII primitives type in any terminal, no keyboard layout needed |
| Prototyping on a phone or tablet | **J** | Official iOS and Android builds exist |
| Research into array-language semantics | **BQN** | The specification is the artefact — self-hosted compiler included |

## J: The Deep, Patient Workhorse

J takes APL's ideas and refuses to require a special keyboard. Every primitive is ASCII: `+/` sums, `*:` squares, `#` counts, `%` divides. That single design decision is why J still has a user base in finance, actuarial work, and signal processing where nobody wants to remap their keyboard to type a language.

Installation is deliberately boring. Official builds cover Windows, Linux, macOS, iOS, Android, and Raspberry Pi; on Linux you launch `jconsole` for the terminal REPL or `jqt` for the GUI IDE. Building from source is documented via the repository's `overview.txt`, and shipped distributions are produced by GitHub Actions — so the engine source and the releases track each other.

Here is J doing what arrays are for:

```j
   +/ i. 100          NB. sum of 0..99        → 4950
   +/ *: i. 10        NB. sum of squares 0..9 → 285
   mean =: +/ % #     NB. fork: sum ÷ tally
   mean 3 1 4 1 5     NB. → 2.8
```

Four lines, no loops, no imports. The `mean =:` definition is a **fork**: `+/ % #` is read right-to-left as "sum divided by count", applied to the argument. Once that clicks, the density stops looking arbitrary and starts looking like shorthand you wished Python had.

Two J specifics worth knowing. First, evaluation is strictly **right to left** with no operator precedence — `2*3+4` is 14, not 10. Second, the wiki at jsoftware.com is the real product: thousands of pages of worked examples, release notes going back decades, and a vocabulary page that doubles as the reference manual. For a language whose symbols are terse, that documentation is the difference between "clever" and "maintainable".

## BQN: A Modern Redesign With a Fast Engine

BQN started from a simple question: if you designed an array language today, knowing everything APL's users learned the hard way for sixty years, what would it look like? The answers show up as clean semantics, consistent glyph roles, a first-class function/array distinction, and a **specification precise enough to be implemented by a self-hosted compiler**.

The main repository (`mlochbaum/BQN`, 1,076 stars) holds the spec, documentation, and a BQN implementation written in BQN. The implementation you actually run is **CBQN** (`dzaima/CBQN`, 407 stars, committed the same week this article was written): a C engine with bytecode compilation and mostly native primitives. The project's own performance notes claim CBQN beats the fastest array languages much of the time — a claim that is credible given the engineering effort in its build system.

Building CBQN is refreshingly direct:

```bash
git clone https://github.com/dzaima/CBQN.git && cd CBQN
make                  # development-friendly build
make o3n              # optimised for the CPU you are on (x86-64)
sudo make install     # installs as /usr/local/bin/bqn
sudo make uninstall   # clean removal
```

`PREFIX=/some/path make install` relocates the install, and `make clean` resets the build. If you would rather not compile, distribution packages exist for Alpine Linux, Nix, Guix, FreeBSD Ports, Arch AUR (`cbqn-git`), and Spack — and browser-hosted BQN environments mean you can try the language before installing anything.

BQN in practice looks like this:

```
   +´ ↕100          # sum of 0..99 → 4950
   +´ ÷ ≠ 3‿1‿4‿1‿5 # mean → 2.8
```

`↕100` generates the vector, `+´` folds addition over it, and `+´ ÷ ≠` is the classic fork for "sum over length". BQN's glyph set is larger than J's ASCII vocabulary but far more regular: the same visual shape tends to mean the same conceptual role across primitives. If you care about language design as a subject, BQN is the most interesting thing in this category since APL itself.

## April: APL as a Library Inside Common Lisp

April attacks the problem from the opposite direction. Instead of a standalone interpreter, it **compiles a subset of APL into Common Lisp**, which means an APL expression becomes a macro expansion in a system you already run, debug, and deploy. If your application is a Lisp service that occasionally needs to crunch matrices, April gives you APL's notation without a second runtime.

Installation is a Quicklisp form, and the README notes April has been verified against SBCL, CCL, ECL, ABCL, Clasp, Allegro CL, and LispWorks — with SBCL and CCL considered fully compatible without special provisions. That compatibility note matters: array performance follows the host compiler, so the free-threaded, aggressively optimised Lisps get the best numbers.

```lisp
(ql:quickload 'april)

(april "1+2 3 4")                       ; → 3 4 5
(april "mean←+/÷≢ ⋄ mean 3 1 4 1 5")    ; → 2.8
(april-f "+/2 3 4")                     ; formatted array output
(april (demo))                          ; prints a tour of the language
```

Two entry points do the work: `(april "...")` evaluates an APL string and returns the value, while `(april-f "...")` prints in traditional APL array layout before returning — genuinely easier to read than Lisp's array printing. Environment settings are passed as a parameter list, for example adjusting the index origin:

```lisp
(april (with (:state :count-from 0)) "⍳9")   ; 0 1 2 3 4 5 6 7 8
```

That index-origin knob is a small example of a large truth about array languages: **the notation is the easy part; the conventions are where bugs live.**

## Pitfalls That Cost Newcomers a Weekend

- **Right-to-left evaluation.** J and APL have no operator precedence; everything evaluates right to left. Expressions that look unambiguous in a left-to-right language mean something else here.
- **Index origin differs between systems.** APL traditions mostly count from 1; many modern dialects default to 0. Never port indexing code without checking `⎕IO` (or April's `count-from`).
- **Glyph input is a real workflow decision.** BQN and APL need Unicode input via keyboard layouts and editor integrations. J's ASCII primitives avoid this entirely — a legitimate reason to pick J for teams, not a stylistic preference.
- **Intermediate arrays eat memory.** Array languages materialise results: a chain of operations on a million-element vector can hold several copies at once. Prefer fused expressions over intermediate variable assignments when memory is tight.
- **Integer and floating-point boundaries.** Mixing machine integers and floating point changes results subtly, especially in reductions. Check the type of your `i.`/`↕` generator before trusting a sum.
- **Tacit style is hard to debug.** Point-free definitions are elegant and opaque in equal measure. Write explicit definitions with named arguments first, then refactor to trains once the code is correct.
- **Host-compiler dependency in April.** Performance and some library tests follow the Common Lisp implementation — the README documents failures on JVM-based ABCL and compatibility issues on Allegro CL and LispWorks. Benchmark on the Lisp you will actually deploy.
- **J version churn.** J9.7 landed in April 2026 with new language features and a J9.8 beta already circulating. Pin the version your scripts are tested against and read the release notes before upgrading.

## Why Run These Locally at All?

Array languages are interactive by nature. The productive loop is "type a fragment, look at the shape of the result, adjust" — and every one of these three is designed around a REPL that responds in milliseconds. That loop survives a hosted notebook environment, but it dies in a containerised batch pipeline where you rebuild to test a thought. The engines are also tiny: CBQN compiles to a single binary with no runtime dependencies, and J ships as a self-contained interpreter, so there is no cost argument for outsourcing them to compute you rent by the hour.

If your interest is really in compact, expressive toolchains rather than arrays specifically, our [Scheme implementations comparison](../2026-09-13-scheme-implementations-racket-chez-guile-comparison/) covers the same trade-off in the Lisp family, the [Julia web frameworks comparison](../2026-09-04-julia-web-frameworks-genie-oxygen-httpjl-comparison/) shows how a modern numerical language handles services, and the [self-hosted Compiler Explorer guide](../2026-06-18-self-hosted-compiler-explorer-godbolt-code-analysis/) explains how to run a local compiler playground for quick experiments.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Array Languages in 2026: J vs BQN vs April Compared",
  "description": "A practical 2026 comparison of open-source array languages: J9.7 (ASCII APL descendant), BQN with the CBQN C engine, and April, which compiles APL into Common Lisp. Includes real install commands and code examples.",
  "datePublished": "2026-09-14",
  "dateModified": "2026-09-14",
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

**What is an array language, in one paragraph?**
An array language treats entire collections as single values: adding two vectors is one operation, not a loop over elements. You write transformations on whole arrays and the interpreter handles iteration, often with vectorised or multithreaded internals. APL, J, BQN, K, and their relatives are the classic examples, and R's vector operations and NumPy's broadcasting are diluted, partial versions of the same idea.

**Should I learn J or BQN first in 2026?**
Learn BQN first if you care about understanding the design space — the specification is short, consistent, and readable. Learn J first if you want the widest documentation and the least terminal friction, since its ASCII primitives need no keyboard layout. Both will teach you array thinking within a week; the languages are more similar than their glyph sets suggest.

**Is APL-style code maintainable in a team setting?**
It is maintainable in the same way a dense regular expression is: fine for two or three people who share the notation, hostile to everyone else. The mitigation is the same in both cases — comment the intent, keep complex expressions named and tested, and avoid point-free style in code other people will read. Teams that adopt array languages successfully usually confine them to numerical kernels with clear interfaces.

**How do these compare to NumPy or pandas for data work?**
NumPy gives you array primitives with Python's syntax and ecosystem; an array language gives you notation designed around arrays from the ground up, plus a REPL-centric workflow. The practical difference shows up in exploratory analysis with many small transformations, where six characters beat six lines. For production pipelines that must interoperate with the wider Python or SQL world, NumPy remains the pragmatic choice.

**Do array languages handle strings and files, or only numbers?**
All three handle characters and strings — J and BQN treat strings as character arrays, and J in particular has a strong string-processing vocabulary. April inherits Common Lisp's I/O facilities, which are broader than anything APL ever offered. Array languages are at their weakest in idiomatic "glue" work like parsing messy JSON, which is why they usually appear as a component rather than the whole system.

**Can I embed BQN or April inside an existing application?**
Yes, and that is one of the strongest reasons to pick them. CBQN exposes an embedding interface for host languages, with bindings demonstrated from Rust and a JavaScript implementation for browser work. April is by definition embedded — it compiles APL into Common Lisp, so it ships as part of your Lisp program with no external process to manage.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
