---
title: "Chibi-Scheme vs Gambit vs Gerbil in 2026: The Definitive Guide to R7RS Toolchains"
date: "2026-09-30"
tags: ["scheme", "programming-languages", "compilers", "developer-tools", "r7rs"]
draft: false
description: "A practical comparison of three Scheme implementations that still see active development in 2026: chibi-scheme, Gambit and Gerbil. Install commands, embedding strategies, and which one to pick."
---

Most language comparisons are written about languages nobody ships with. Scheme is different: it is 50 years old, it is the source of half the ideas in modern JavaScript and Rust, and in 2026 there are still three implementations — **chibi-scheme**, **Gambit** and **Gerbil** — receiving commits *this week*. If you want a small scripting runtime to embed in a C program, a compiler that turns Scheme into fast standalone binaries, or a batteries-included dialect for writing real applications, the decision is not academic.

This is the practical guide: real install commands from each project's own README, honest notes about where each one hurts, and a clear verdict per use case.

## TL;DR — Quick Verdict

- **Pick chibi-scheme** to embed a Scheme interpreter inside a C or C++ application. It builds a shared `libchibi-scheme`, it is R7RS-small compliant, it compiles to WebAssembly via emscripten, and the whole thing is a few hundred kilobytes (1,400 stars, commits 2026-09-27).
- **Pick Gambit** when you want speed and native output. It compiles Scheme to C, supports whole-program optimization with `--enable-single-host`, and has the most mature module system of the three (1,444 stars, commits 2026-09-29).
- **Pick Gerbil** when you want to *build software* rather than admire a language. It layers a macro and module system on the Gambit runtime, ships a standard library with networking and crypto bindings, and is the only one of the three with precompiled release packages (1,270 stars, LGPL-2.1, v0.18).

None of them is a Racket replacement, and none of them wants to be. They are small, fast, embeddable, and they will still compile your code in ten years.

## Comparison Table (September 2026)

| Feature | chibi-scheme | Gambit | Gerbil |
|---|---|---|---|
| Role | Embeddable R7RS interpreter | Native compiler + runtime | Dialect + stdlib on Gambit |
| Implementation | C (C99) | C (compiles Scheme → C) | Scheme on Gambit |
| GitHub stars | 1,400 | 1,444 | 1,270 |
| Last commit | 2026-09-27 | 2026-09-29 | 2026-07-22 |
| License | BSD-style (see repo) | Dual Apache-2.0 / LGPL (see repo) | LGPL-2.1 |
| Standard target | R7RS-small | R7RS library system, large SRFI set | R7RS libraries + own dialect |
| Build | `make && make test` | `./configure && make -j8` | `./configure && make -j4` |
| Output | `libchibi-scheme` shared library | `gsi` interpreter, `gsc` compiler, `-exe` binaries | `gxi` interpreter, `gxc` compiler |
| Native binary output | No (interpreter + C API) | **Yes** | Yes (via Gambit) |
| Embedding in C | **Best in class** | Supported, heavier | Not the intended use |
| WebAssembly | **Yes** (`make js`) | No | No |
| Package ecosystem | snow-fort R7RS libraries | Git-hosted modules, permissive | Bundled stdlib + own package index |
| External dependencies | None | None beyond a C toolchain | sqlite, zlib, OpenSSL |
| Best for | Embedding, small scripts | Native performance | Writing applications |

## Decision Matrix: 10 Seconds to a Verdict

| Your goal | Recommended | Why |
|---|---|---|
| Add a scripting layer to a C/C++ game engine | **chibi-scheme** | Shared library, tiny footprint, C API designed for the job |
| Run Scheme in the browser | **chibi-scheme** | `make js` emscripten target is maintained in-tree |
| Ship a single-file executable with no runtime install | **Gambit** | `gsc -exe` produces a standalone binary |
| Maximum numeric throughput from Scheme | **Gambit** | `--enable-single-host` compiles the whole program as one C unit |
| Write a network service in Scheme | **Gerbil** | Bundled stdlib with sockets, TLS and SQLite bindings |
| Learn Scheme properly with real R7RS semantics | **chibi-scheme** | Smallest surface area; the report is the documentation |
| Distribute to colleagues without a build step | **Gerbil** | Precompiled v0.18 packages for Ubuntu, Debian, Fedora, CentOS |
| Extend another Lisp-flavoured runtime | None here | See the embedded Lisp comparison below |

## chibi-scheme: The Interpreter You Embed

chibi-scheme is the smallest serious Scheme in active development. Its README is refreshingly blunt about what it is: an implementation of *R7RS small*, built as a shared library, with an emscripten target for the browser.

Installation is two commands and assumes GNU make:

```bash
# From a source checkout
make && make test        # build and run the test suite
sudo make install        # installs to /usr/local by default

# Custom prefix, no sudo
make PREFIX=$HOME/.local/
make PREFIX=$HOME/.local/ install
```

The build produces **`libchibi-scheme`** plus the `chibi-scheme` binary. Running a script is exactly what you would expect:

```bash
cat > hello.scm <<'EOF'
(import (scheme base) (scheme write))
(display "hello from R7RS") (newline)
EOF

chibi-scheme hello.scm
```

The interesting part is the embedding story. Because the interpreter is a library, a C host can evaluate expressions and call back into Scheme without spawning a process:

```c
#include <chibi/eval.h>

int main(int argc, char **argv) {
  sexp ctx = sexp_make_eval_context(NULL, NULL, NULL, 0);
  sexp_load_standard_env(ctx, NULL, SEXP_SEVEN);
  sexp_eval_string(ctx, "(import (scheme base)) (+ 40 2)", -1, NULL);
  return 0;
}
```

What you give up for that footprint: there is no native code generation, so long-running numeric loops stay interpreted. For anything CPU-bound you would either write the hot path in C or choose Gambit. There is also no single blessed package manager — the wider R7RS ecosystem lives across community library indexes, so dependency management is a manual exercise in `curl` and path configuration.

**Verdict:** the right answer for embedding and for browser-side Scheme. Unbeatable size-to-capability ratio.

## Gambit: Compile Scheme to C, Then to a Binary

Gambit is the performance option. It compiles Scheme to C, and its headline build flag fuses the entire program into a single translation unit so the C compiler can optimize across module boundaries:

```bash
./configure --enable-single-host --enable-march=native --enable-dynamic-clib
make -j8          # build runtime library, gsi and gsc
make check        # run self tests (optional but recommended)
make doc          # build the documentation
```

Two binaries come out of the build: **`gsi`**, the interpreter for interactive work, and **`gsc`**, the compiler. The workflow mirrors that of a systems language:

```bash
# Interpret during development
gsi -e '(display (map (lambda (x) (* x x)) (iota 10)))'

# Compile a standalone executable
cat > fib.scm <<'EOF'
(define (fib n) (if (< n 2) n (+ (fib (- n 1)) (fib (- n 2)))))
(display (fib 30)) (newline)
EOF

gsc -exe fib.scm
./fib
```

Gambit's module system is where it pulls ahead of chibi for application work: modules are ordinary Scheme libraries, and because the module mechanism is file-and-git oriented, third parties distribute R7RS libraries simply by publishing a repository. That is a pragmatic design — no central registry to rot — but it also means there is no `install` command that resolves transitive dependencies for you. You vendor code deliberately, and you read what you vendor, which for a language toolchain is not a bad trade at all.

The dual Apache-2.0 / LGPL posture (the Gerbil README explicitly restates the Gambit license as dual LGPLv2.1 + Apache 2.0) makes Gambit safe to link against in commercial products, which is precisely why it shows up inside shipping desktop applications.

**Verdict:** fastest of the three on numeric code and the only one that produces a self-contained native executable. The build is heavier and the documentation is thinner than what modern developers expect.

## Gerbil: A Dialect With Batteries Included

Gerbil is built *on* Gambit — same runtime, same compiler lineage — but adds a macro system, a module system and a standard library. The project describes itself as a macro and module system on top of the Gambit runtime and compiler, and the practical consequence is that you stop writing your own libraries.

Installation wants three system dependencies first:

```bash
sudo apt install libssl-dev zlib1g-dev libsqlite3-dev

./configure
make -j4
sudo make install          # installs into /opt/gerbil
# or: ./configure --prefix=/path/to/installation
```

Precompiled **v0.18** packages exist for Ubuntu, Debian, Fedora and CentOS, and there is a Homebrew formula for macOS (`brew install mighty-gerbils/gerbil/gerbil-scheme`) — the only one of the three projects that offers anything other than a source build.

Gerbil gives you `gxi` for scripts and `gxc` for compilation, plus built-in bindings for the things real programs need: sockets, TLS, and SQLite via the `libsqlite3` dependency it compiles against. A minimal HTTP-facing program does not require assembling four libraries from git:

```scheme
;; hello.ss — run with: gxi hello.ss
(import :std/net/httpd
        :std/text/json)

(define (handler req res)
  (http-response-write res 200
    '(("Content-Type" . "application/json"))
    (string->bytes (json-object->string
                     (hash ("status" "ok") ("service" "gerbil"))))))

(start-http-server! "0.0.0.0:8080" handler: handler)
```

Its SRFI coverage is also notably complete, and interestingly its implementations of SRFI 115 and SRFI 159 are borrowed from chibi — a nice illustration that these projects read each other's source rather than competing for namespace.

The costs are real: three system libraries must be present before you build, the last commit was 2026-07-22 (slower cadence than the other two), and because Gerbil is its own dialect with its own idioms, code you write for it will not run unchanged on chibi or in a strict R7RS host.

**Verdict:** the best choice for writing a *program* rather than a script. If you want Scheme to behave like a modern language with a standard library, this is it.

## Pitfalls and Migration Notes

- **Interpreter vs compiler is not a detail.** A chibi-scheme script that runs fine on your laptop can be orders of magnitude slower than the same code compiled by Gambit with `--enable-single-host`. Benchmark before committing to an embedding strategy.
- **`--enable-single-host` increases build time and memory usage.** It is the right default for release builds and the wrong one for rapid iteration; keep a second build directory for the fast path.
- **Gerbil needs a C toolchain and OpenSSL, zlib and SQLite headers present before configure runs.** Missing `libssl-dev` produces a configure failure that reads like a Scheme bug, not a system dependency problem.
- **chibi's `make js` target must be invoked as plain `make js`, not `emmake make js`** — the README calls this out explicitly, and getting it wrong produces a confusing toolchain error.
- **Library portability is the biggest hidden cost.** chibi targets R7RS-small precisely; Gerbil is deliberately permissive about extensions. Code written against Gerbil's `:std/...` namespaces will not run in a strict host, so decide early whether portability or productivity matters more.
- **Do not expect a package manager to save you.** chibi and Gambit both live in a world of git-hosted libraries. Pin commits, vendor your dependencies, and read the source — that is the ecosystem's contract.

## Why This Niche Still Matters

Scheme is the language you reach for when the runtime must be small, the semantics must be defined by a standard you can read in an afternoon, and you refuse to ship a 200 MB dependency tree. That combination is rare and getting rarer: game engines, boot firmware, embedded controllers and browser toys all benefit from a 300 KB interpreter with proper tail calls and lexical scope.

If you are weighing Scheme against other small runtimes, our [embedded Lisp comparison covering Janet, Fennel and Hy](../2026-09-23-embedded-lisp-janet-fennel-hy-comparison/) is the closest sibling to this article, and the [Racket vs Chez vs Guile](../2026-09-13-scheme-implementations-racket-chez-guile-comparison/) breakdown covers the larger implementations in the family. For a very different take on small-language ergonomics, see the [Raku web frameworks comparison](../2026-09-23-raku-web-frameworks-cro-bailador-humming-bird/), and if your interest is command-line tooling in general, the [Rust CLI parser roundup](../2026-08-10-rust-cli-parsers-clap-argh-bpaf/) is worth an hour.

## FAQ

**Is Scheme still worth learning in 2026?**
Yes, and not for nostalgia. SICP-era Scheme teaches composition, recursion and continuations better than almost any other language, and R7RS-small is a specification compact enough to read fully. The three implementations here are actively maintained, so your code will still run.

**Which implementation is fastest?**
Gambit, in nearly every benchmark that involves computation rather than I/O — especially with `--enable-single-host`, which lets the C compiler optimize across the whole program. Gerbil inherits Gambit's runtime but adds library overhead; chibi is interpreted and slowest on tight loops.

**Can I call C code from these implementations?**
Yes. chibi-scheme exposes a full C API and is designed to be driven from a host program, and Gerbil ships FFI support with system library bindings. Gambit compiles to C directly, so C interoperation is native to its model.

**Do I need to install a package manager?**
No. chibi builds with `make`, Gambit with `./configure && make`, and Gerbil with `./configure && make -j4` plus three system libraries. Library resolution beyond that is manual for chibi and Gambit; Gerbil bundles most of what you need in its standard library.

**What is the practical difference between Gambit and Gerbil?**
Gerbil *is* Gambit underneath, plus a macro system, a module system and a standard library. Choose Gambit for maximum control and smallest build surface; choose Gerbil when you would rather write application code than build infrastructure first.

**Can I run any of them in a container?**
All three build from source in a `debian:stable-slim` image with `build-essential` (plus `libssl-dev zlib1g-dev libsqlite3-dev` for Gerbil), so a multi-stage Dockerfile producing a distroless runtime image is straightforward if you compile to a native binary with Gambit or Gerbil.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Chibi-Scheme vs Gambit vs Gerbil in 2026: The Definitive Guide to R7RS Toolchains",
  "description": "A practical comparison of three Scheme implementations that still see active development in 2026: chibi-scheme, Gambit and Gerbil. Install commands, embedding strategies, and which one to pick.",
  "datePublished": "2026-09-30",
  "dateModified": "2026-09-30",
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
