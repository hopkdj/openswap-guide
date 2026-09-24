---
title: "TCC vs chibicc vs cproc in 2026: Which Tiny C Compiler Should You Actually Use?"
date: "2026-09-24"
tags: ["c-programming", "compilers", "developer-tools", "embedded", "open-source"]
draft: false
cover: "/img/screenshots/tcc-logo.jpg"
---

Every C developer has felt it: you change one line, and the build system grinds for ninety seconds to reprocess a dependency graph you have not touched since Tuesday. Full toolchains like GCC and Clang are engineering marvels, but they are also enormous — hundreds of megabytes of binaries carrying decades of optimization passes you did not ask for on an edit-compile-run loop.

Tiny C compilers attack that problem from the opposite direction. Instead of optimizing hard, they optimize for **speed of compilation, tiny footprint, and installability on systems where nothing else fits** — rescue disks, microcontrollers, bootstrap environments, and teaching labs. In 2026 three projects dominate this space, and they make very different trade-offs.

## TL;DR: The 30-Second Verdict

- **Need a fast, practical C compiler you can actually ship with today?** → **TCC**. It compiles roughly 10× faster than `gcc -O0`, generates real executables, and even runs C as a script.
- **Want to *understand* how a C compiler works, or teach one?** → **chibicc**. It is the cleanest readable C11 implementation in existence, built step by step alongside a book.
- **Want a standards-focused compiler that boots up its own compiler to test itself?** → **cproc**. It leans on the QBE backend, tracks C23, and proves correctness with a self-hosting bootstrap.

If you remember one line: **TCC for speed and practicality, chibicc for clarity, cproc for standards discipline.**

## The Three Contenders Side by Side

Live GitHub data pulled on **September 24, 2026**:

| | **TCC** | **chibicc** | **cproc** |
|---|---|---|---|
| Repository | tinycc/tinycc | rui314/chibicc | michaelforney/cproc |
| Stars | **3,038** | **11,909** | **847** |
| Last push | 2026-09-22 | 2023-10-30 | 2026-06-02 |
| Primary language | C | C | C |
| License | LGPL-2.1 | MIT | ISC |
| Architecture | One-pass compiler | Multi-pass (tokenize → preprocess → parse → codegen) | Frontend + QBE backend |
| Language coverage | Heading toward full ISO C99 | Almost all mandatory C11 features | Most of C11 plus many C23 features |
| Optimization | Minimal; optional bounds checker | None ("emits terrible code") | Whatever QBE provides |
| Targets | i386, x86_64, arm, aarch64, riscv64 | x86-64 primarily | x86_64, aarch64, riscv64 |
| Self-hosting | Yes, compiles itself | Yes (also compiles Git, SQLite, libpng) | Yes, with byte-identical bootstrap |
| Shared libraries / PIC | Yes | Limited | Not implemented |
| Best for | Fast edit-compile loops, scripting in C, rescue environments | Learning, teaching, reading | Conformance work, bootstrapping minimal systems |

## Use-Case Decision Matrix

| Your situation | Pick | Why |
|---|---|---|
| Course or self-study on compiler construction | chibicc | Every commit maps to one chapter of the book |
| You need `gcc`-like compile speed on a laptop | TCC | The fastest of the three by a wide margin |
| Tiny build environment (initramfs, rescue image) | TCC | Smallest toolchain footprint and no runtime deps |
| You need C23 features from a small compiler | cproc | It tracks C23 explicitly and documents the gaps |
| You must audit the source before trusting it | chibicc or cproc | Both are readable end-to-end; cproc is ISC-licensed |
| You need `-shared` / position-independent output | TCC | cproc does not generate PIC at all |
| You want deterministic self-validation in CI | cproc | `make bootstrap` verifies byte-identical stages |

## TCC: The Practical Tiny Compiler

TCC — the Tiny C Compiler by Fabrice Bellard — is the veteran of this group and the only one you would hand to a teammate who just wants something that works. Its README makes four claims and, unusually, all four hold up: it is **small**, **fast** (roughly ten times faster than `gcc -O0`), **unlimited** in that any C dynamic library can be used directly, and it includes an **optional memory and bound checker** that can be mixed with normal code.

Installation from source, straight from the repository README:

```bash
./configure
make
make test
make install
```

Two features stand out in daily use. First, `tcc -run` compiles and executes in a single step with no intermediate files:

```bash
# compile and run directly, no output binary
tcc -run hello.c

# turn a C file into a script
#!/usr/local/bin/tcc -run
#include <stdio.h>
int main(int argc, char **argv) {
    printf("hello %s\n", argc > 1 ? argv[1] : "world");
    return 0;
}
```

After `chmod +x hello.c` that file behaves like a shell script — command-line arguments arrive in `argc`/`argv` exactly as ANSI C specifies. If you write tooling where a throwaway C program is faster than a Python script, this is the most pleasant workflow available anywhere.

Second, the bounds checker. Compiling with `tcc -b` instruments pointer arithmetic and memory accesses so out-of-bounds reads and writes abort with a diagnostic instead of corrupting memory silently:

```bash
tcc -b -g -o app app.c && ./app
```

That is genuinely useful for debugging a segfault in a small program without reaching for Valgrind. TCC is one-pass and does minimal optimization, so do not expect `-O2`-class codegen — the value here is turn-around time, not throughput.

Install TCC when you want the compile step to disappear from your loop.

## chibicc: The Compiler You Can Actually Read

chibicc author Rui Ueyama — creator of the original current-generation LLVM `lld` linker — wrote this compiler as the reference implementation for a book on C compilers and low-level programming. The result is the most rewarding small compiler to read: each commit corresponds to one section of the book, and the codegen, parser, and preprocessor are laid out with a first-time reader explicitly in mind.

It is not a toy in coverage terms. chibicc supports almost all mandatory features and most optional features of **C11**, including:

- A full preprocessor
- `float`, `double`, and 80-bit `long double` via x87
- Bit-fields, `alloca()`, variable-length arrays, compound literals
- Thread-local and atomic variables
- Common symbols and designated initializers
- Functions that take or return structs by value per the x86-64 System V ABI

More importantly, it compiles real software without patches: **Git, SQLite, libpng, and chibicc itself**, and the resulting binaries pass those projects' own test suites.

Two caveats matter for 2026 planning. First, **there is no optimization pass** — the README says plainly that it emits code "probably twice or more slower than GCC's output", with an optimization pass only planned once the frontend was finished. Second, the repository was **last updated in October 2023**. It is effectively complete-as-a-book rather than maintained-as-a-tool, and pull requests are intentionally not merged because history is rewritten to keep every commit bug-free.

Use chibicc when the goal is comprehension. It is the best-documented path from "what is a tokenizer" to "my compiler emits x86-64 assembly".

## cproc: Standards Discipline with a QBE Backend

cproc takes a third route: a C frontend written in C99, paired with **QBE** as its code generator. It is ISC-licensed, implements most of C11 and a growing slice of **C23**, and it was last active in June 2026, which makes it the most actively maintained of the two smaller options.

```bash
./configure     # writes config.h and config.mk for your target
make
```

The build system also encodes a strong correctness claim. Beyond the normal `make`, it offers bootstrap targets:

- `stage2` — rebuild the compiler using the stage-1 output
- `stage3` — repeat once more
- `bootstrap` — build both and **verify the two stages are byte-wise identical**

That byte-identical bootstrap is the same technique used to validate GCC and other critical toolchains, and it is a genuinely useful CI check if you plan to trust a small compiler in a build pipeline. Tested targets include `x86_64-linux-musl`, `x86_64-linux-gnu`, `x86_64-freebsd`, `aarch64-linux-musl`, `aarch64-linux-gnu`, and `riscv64-linux-gnu`.

The honest limitations list is long, and you should read it before committing:

- **No position-independent code** — no shared libraries, modules, or PIEs
- `volatile`-qualified types and `long double` are not implemented
- The preprocessor is **not fully implemented**, so an external one is required at runtime
- Complex types and atomic types (both optional in C11) are missing
- C23 gaps remain around `constexpr`, `auto`, and `#embed`
- Inline assembly needs QBE support and is not there yet

cproc also does not implement multiple C versions. Code affected by breaking changes between standard revisions must be updated or patched, which is a deliberate policy rather than an oversight — the project would rather follow the standard than accumulate compatibility switches.

Use cproc when you want a small compiler with an explicit conformance target, an auditable license, and a self-verifying build.

## Where Tiny Compilers Still Win in 2026

It is reasonable to ask why these projects exist at all when GCC and Clang are free. Three answers keep coming up in practice.

**Bootstrap and rescue environments.** A toolchain that compiles in seconds and occupies a few megabytes fits on an initramfs, a recovery image, or a container you want to keep under 100 MB. TCC's own documentation cites compiling and running C code "everywhere, for example on rescue disks" as a design goal.

**Edit-compile-run latency.** For small programs, the compiler's own startup and preprocessing dominate the build. A compiler that finishes in 20 ms changes how you write code — you stop batching changes and start experimenting. Optimizing for developer iteration speed rather than runtime speed is a legitimate engineering choice, and none of these projects pretends otherwise.

**Education and auditability.** You cannot read GCC's optimizer, and you cannot hold its architecture in your head. A compiler whose stages fit in one repository — chibicc's tokenizer, preprocessor, parser, and codegen, or cproc's frontend plus QBE — is something a single person can fully understand and therefore fully trust.

To see generated code side by side, our [self-hosted Compiler Explorer guide](../2026-06-18-self-hosted-compiler-explorer-godbolt-code-analysis/) shows how to run a multi-compiler assembly viewer on your own hardware. If you are building the frontend yourself rather than using a complete one, the [lexer generator comparison covering flex, re2c, and ragel](../2026-06-26-lexer-generator-tools-flex-re2c-ragel/) is the natural next read. And when your compiled binaries are destined for firmware, our [firmware emulation comparison of Renode, QEMU, and gem5](../2026-09-23-firmware-emulation-renode-qemu-gem5-comparison/) covers how to test them without hardware.

## Pitfalls and Hard Limits

- **Do not ship `-O2` expectations to a tiny compiler.** None of these three will match GCC or Clang on generated-code performance. Profile before you commit to one for anything throughput-sensitive.
- **Missing PIC is a hard wall, not a tuning issue.** cproc cannot produce shared libraries at all. If your build needs `-fPIC` or `-shared`, stop and use TCC or a full toolchain.
- **An external preprocessor is part of cproc's runtime.** "Just cproc" is not a complete toolchain — you need QBE, an assembler, a linker, and a preprocessor on the target system.
- **Stale repositories are a maintenance risk.** chibicc has not moved since October 2023 and its author explicitly declines pull requests. Treat it as a stable artifact to read, not a compiler to file bugs against.
- **TCC is LGPL-2.1, cproc is ISC, chibicc is MIT.** If you embed a compiler in a product, the license difference is not academic — LGPL has obligations that ISC and MIT do not.
- **The bounds checker is a debugging tool.** Enabling it changes memory behaviour and slows execution. Keep it out of release builds.
- **Self-hosting proves less than it seems.** Compiling yourself is a strong smoke test, but it does not prove conformance. Keep a conformance test suite in your pipeline if correctness matters.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "TCC vs chibicc vs cproc in 2026: Which Tiny C Compiler Should You Actually Use?",
  "description": "An in-depth 2026 comparison of the three leading tiny C compilers: TCC, chibicc, and cproc. Covers live GitHub stats, official build commands, language coverage, self-hosting bootstrap, performance limits, and licensing.",
  "datePublished": "2026-09-24",
  "dateModified": "2026-09-24",
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

### Is TCC good enough for production code?

For small utilities, build scripts, bootstrapping, and internal tooling — yes, and it is often the pragmatic choice. For latency-sensitive production binaries where codegen quality matters, no: TCC does minimal optimization, so pair it with a full compiler for release builds and use TCC for your inner development loop.

### Can chibicc compile real programs, or is it just a toy?

It compiles real ones. chibicc builds **Git, SQLite, libpng, and itself** without modifications, and the resulting executables pass those projects' test suites. Its limitations are optimization quality and maintenance status, not basic capability.

### Does cproc support shared libraries?

No. Generation of position-independent code — shared libraries, modules, and PIEs — is not implemented. If your target needs `.so` files, use TCC or a mainstream compiler.

### Which of the three compiles fastest?

TCC by a clear margin: its documentation claims compilation and linking roughly ten times faster than `gcc -O0`. chibicc is explicitly unoptimized in both its output and its ambitions, and cproc's speed depends on QBE, so it lands between the two.

### Can I use these compilers for microcontrollers and embedded targets?

TCC targets i386, x86_64, arm, aarch64, and riscv64; cproc covers x86_64, aarch64, and riscv64 through QBE. Both are viable on 32/64-bit embedded Linux. For bare-metal 8/16-bit MCUs you still want a dedicated embedded toolchain, since these projects assume a hosted C environment with a system linker and libc.

### Do any of them support C++?

No. All three are C compilers. TCC has historical limited C++ support in some forks, but none of these projects is a viable C++ toolchain — use GCC or Clang for that.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
