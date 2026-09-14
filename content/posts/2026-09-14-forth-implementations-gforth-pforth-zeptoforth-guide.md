---
title: "Forth in 2026: Gforth vs pForth vs zeptoforth Compared"
date: "2026-09-14"
tags: ["forth", "embedded", "programming-languages", "microcontroller", "developer-tools", "compilers"]
draft: false
---

Most languages in 2026 want to own your whole machine: a runtime, a package manager, a build system, and several hundred megabytes of dependencies. Forth does the opposite. A complete Forth development environment is a few thousand bytes of compiled code, an interactive REPL that can redefine any word while it is running, and a mental model so small that you can hold the entire language in your head.

That minimalism is also why Forth never "won" and why it is still shipping in 2026 — inside bootloaders, satellite firmware, telescope control systems, and a surprising number of hobby boards. Three implementations cover almost every realistic use case today: **Gforth** (the GNU workhorse), **pForth** (portable C, easy to embed), and **zeptoforth** (a serious multitasking Forth for ARM Cortex-M and RP2040/RP2350 microcontrollers). All three are open source and all three were actively developed in 2026.

Here is the honest comparison, with real build commands pulled from each project's own documentation.

## TL;DR: Quick Verdict

**Learning Forth or writing interpretive scripts on a workstation? Use Gforth** — it is the fastest to install, the most standard-compliant, and has the best debugging words. **Embedding a Forth kernel inside a C application or booting it on an unusual CPU? Use pForth** — it is deliberately small, self-contained C, and its dictionary can be saved and reloaded as a binary blob. **Driving real hardware — sensors, motor controllers, RP2040 boards — with multitasking and a live console? Use zeptoforth.** Gforth proves the language is pleasant; zeptoforth proves it is still relevant to hardware.

## The Three Implementations Side by Side

| Implementation | Primary target | Repository | Stars | Last activity | Build system | Licence |
|---|---|---|---|---|---|---|
| **Gforth** | Linux/BSD/macOS workstations | GNU Savannah + `ftp.gnu.org` tarballs (0.7.3) | — (GNU project) | packaged releases; git head active | autoconf / package manager | GPL |
| **pForth** | Hosted C, embedded, cross platforms | `philburk/pforth` | **711** | 2026-07-29 | Makefile or CMake | permissive, embed-friendly |
| **zeptoforth** | Cortex-M, RP2040/RP2350 | `tabemann/zeptoforth` | **353** | 2026-09-08 | GNU Make + arm-none-eabi | open source, microcontroller-focused |

The star counts tell the story correctly for once: pForth's 711 stars come from C developers who want a Forth kernel as a component; zeptoforth's 353 come from embedded engineers who want a Forth *system*.

## Decision Matrix: Pick Your Implementation in Ten Seconds

| Your task | Recommended | Why |
|---|---|---|
| Learn Forth syntax and the stack in an afternoon | **Gforth** | One `apt install`, instant REPL, excellent `see`/`.s` debugging words |
| Script a text-processing pipeline on a server | **Gforth** | Standard file I/O words and floating point work out of the box |
| Embed a Forth interpreter in a C program | **pForth** | Small kernel, clean C source, dictionary can be saved to `.dic` |
| Boot Forth on an unusual CPU or a custom board | **pForth** | Portability is the design goal; `platforms/` already covers cross builds |
| Build a sensor node that stays live-reprogrammable | **zeptoforth** | Multitasking, task monitor, module system, live console over serial |
| Teach an embedded class without an IDE | **zeptoforth + web terminal** | Students paste code into a browser terminal against real hardware |
| Prototype a control loop on a Raspberry Pi Pico | **zeptoforth** | Prebuilt UF2 images flash by drag and drop |

## Gforth: The Reference Implementation You Should Start With

Gforth is the GNU project's Forth. Its value in 2026 is not novelty but completeness: it targets POSIX systems, implements a broad ANS Forth surface plus the standard extension words, and it is the implementation most Forth literature and `test.fs` suites are written against. On Debian and Ubuntu it is one package away:

```bash
sudo apt install gforth          # fastest route on a Debian-family host
gforth                           # interactive REPL
```

For a newer engine or a system without a package, the GNU FTP archive publishes the 0.7.3 tarball, and the classic three-step build still works:

```bash
tar xzf gforth-0.7.3.tar.gz && cd gforth-0.7.3
./configure && make && sudo make install
```

There is one implementation detail worth knowing before you benchmark anything: Gforth ships multiple engines (`gforth-fast`, `gforth-itc`, the default `gforth`). They differ in how aggressively they use dynamic translation and inline threading. `gforth-fast` is the one you want for tight numeric loops; the default is the debugging-friendly engine. Also be aware that distro packages can lag the GNU tarball by years — check `gforth --version` before reporting a "missing word" bug.

A first real program, which also demonstrates why Forth people find the language relaxing:

```forth
\ sum-squares.fs — run with: gforth sum-squares.fs
: sq ( n -- n^2 )  dup * ;
: sum-squares ( n -- total )  0 swap 1+ 1 ?do  i sq +  loop ;

10 sum-squares .   \ => 385
cr bye
```

`dup *` squares a number by duplicating it and multiplying. The loop uses `?do`, which skips the body entirely when the start index is not below the limit — the Forth equivalent of a zero-iteration guard. Definition, compilation, and interpretation of new words all happen in the same session; there is no compile step to wait for.

## pForth: The Embeddable Kernel

pForth exists for people who need a Forth *inside* something else. The C source is organised so the kernel is separable from the platform I/O layer (`csrc/` for the kernel and per-platform I/O, `fth/` and `fth/util/` for Forth-side code), which is exactly the structure you want when the host is a strange board or a bigger C application.

Building on Unix is documented as a two-step process — build the C kernel, then build the Forth dictionary from `system.fth`:

```bash
git clone https://github.com/philburk/pforth.git
cd pforth/platforms/unix
make all
./pforth_standalone
```

The repository also supports CMake if your host build already uses it:

```bash
cmake . && make
cd fth && ./pforth_standalone
```

Once you are inside, the classic smoke test takes three lines, and the dictionary workflow is the feature that distinguishes pForth from a toy interpreter:

```forth
3 4 + .              \ => 7
words                \ list every defined word
c" myapp.dic" SAVE-FORTH    \ snapshot the current dictionary
bye
```

That `.dic` file can be loaded again with `pforth -dmyapp.dic`, or you can run a source file directly with `pforth myprogram.fth`. For embedded work, saving a tested dictionary and shipping it without the compiler saves both flash and boot time. The project ships a core-word conformance test — `cd platforms/unix && make test` runs John Hayes' coretest, which is the closest thing the Forth world has to a standard test suite. If you are porting to a new CPU, run coretest first; it catches cell-size and memory-model mistakes before they become mysterious hardware faults.

The realistic limitation: pForth is a kernel, not a platform. You get the language and the dictionary machinery. Networking, filesystems, and multitasking are your problem — which is the correct trade if you are embedding it in a system that already provides those.

## zeptoforth: Forth That Runs Real Hardware

zeptoforth is the most interesting of the three in 2026, because it treats a microcontroller as a proper multitasking operating system target rather than a bare REPL. It runs on Cortex-M boards and on RP2040/RP2350 devices (Raspberry Pi Pico and friends), and "not-so-small" in its tagline is accurate: modules, tasks, a task monitor, and live code upload are all present.

Building the kernel needs the ARM bare-metal toolchain plus Python 3.9 or later with `venv` support:

```bash
# dependencies: arm-none-eabi gas/binutils toolchain, python3 + venv
make                                # default version
make VERSION=v1.6.0                 # explicit version builds
```

The build emits `obj/zeptoforth.<platform>.bin`, `.ihex`, and `.elf` files per platform, plus UF2 images for the RP2040 and RP2350 families. On a Pico-class board the flashing step is deliberately boring: press BOOTSEL while power-cycling (or type `bootsel` at the console), mount the USB mass storage device, and copy `bin/<version>/rp2040/zeptoforth_kernel-<version>.uf2` onto it.

For STM32 boards the documented helper script drives the flash and console in one shot:

```bash
make clean
make VERSION=<version>
make install VERSION=<version>
utils/make_image.sh <version> <platform> <TTY device> <build>
```

Talking to a running board is where zeptoforth is genuinely pleasant. The author maintains **zeptocom.js**, a browser-based Forth terminal that speaks the protocol properly — upload synchronisation, automatic error detection, `#include` handling, a reboot button, and an "attention" escape that can reach a board whose main task is wedged. If you prefer the terminal you already have, `screen` and `picocom` work but give you neither upload sync nor error detection, so a mistyped line silently corrupts the session. The project also ships `utils/codeload3.sh` as a dependency-free uploader:

```bash
./utils/codeload3.sh [-p <device>] -B 115200 serial mycode.fs
```

Two operational details that surprise newcomers: on ordinary terminal emulators **Control-C reboots zeptoforth** (the kernel detects it on the console and treats it as a reset), and some terminals must assert DTR before the USB CDC console responds at all, or the transmitted data arrives corrupted. Both behaviours are documented, both waste an afternoon if you discover them by accident.

## Pitfalls When Adopting Forth in 2026

- **Cell size is not a constant.** Gforth on a 64-bit workstation uses 64-bit cells; zeptoforth on a Cortex-M uses 32-bit cells. Code written with `@`, `!`, and double-cell arithmetic must be checked per target. Use `cell+` and `cells`, never hard-coded byte offsets.
- **Standard compliance varies.** All three implement a large ANS Forth core, but extension words differ. If a word works in Gforth and not on the board, assume it is an extension, not a bug.
- **No stack traces.** Forth's debugging model is introspective rather than retrospective: `see <word>` decompiles, `.s` shows the stack, `dump` shows memory, and `trace` steps. Budget time to learn these four before blaming the compiler.
- **Floating point is optional hardware.** On microcontroller targets, floating-point words may be soft-float, slow, or absent. Prefer fixed-point scaling in hot loops.
- **Dictionary versioning in pForth.** A `.dic` saved by one build may not load in another. Treat dictionaries as build artifacts and regenerate them, never commit them as long-lived binaries.
- **Toolchain drift for zeptoforth.** The kernel is built with `arm-none-eabi` binutils; a mismatched toolchain produces link errors or, worse, a kernel that boots and faults. Pin the version in CI.
- **The console is not a debugger.** On a wedged board the console may be unusable. Know your reset path — the UF2 bootloader on RP2040 class boards is the reliable escape hatch, and zeptoforth's attention escape only works if the console machinery is still alive.
- **Forget the ecosystem expectations.** Forth libraries exist, but you are far more likely to write the word you need than to install one. That is the deal: no dependencies in exchange for fewer abstractions.

## Why Run Forth Toolchains Locally Instead of in the Cloud?

Forth's whole value proposition is proximity to the metal, and that does not survive a hosted build service. **Flashing requires a physical USB connection** — there is no remote equivalent of drag-and-drop UF2, no cloud service that can press BOOTSEL on a Pico. **The REPL is the development process**: you edit a word, recompile it into the running system, and observe behaviour in seconds. Latency through a hosted environment destroys exactly the loop that makes Forth productive. And the toolchains are light enough that there is no economic argument for outsourcing them: Gforth, pForth, and zeptoforth together need a fraction of the disk space that one container image of a modern web framework consumes.

If compiled-systems trade-offs interest you, our [Zig vs Rust vs Go comparison](../2026-09-02-zig-vs-rust-vs-go-systems-programming-guide/) covers how modern languages approach the same low-level territory, and the [embedded C HTTP libraries comparison](../2026-09-04-embedded-c-http-libraries-mongoose-civetweb-libmicrohttpd/) is a useful companion when your microcontroller project needs networking. For other niche toolchains worth knowing, see our [open-source COBOL toolchain guide](../2026-09-14-gnucobol-vs-superbol-vs-cobol-check-open-source-cobol-toolchain/) and the [open-source FPGA development toolchain comparison](../2026-06-07-open-source-fpga-development-toolchain-yosys-iverilog-ghdl-nextpnr/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Forth in 2026: Gforth vs pForth vs zeptoforth Compared",
  "description": "A practical 2026 comparison of three open-source Forth implementations: Gforth for workstation development, pForth as an embeddable C kernel, and zeptoforth for Cortex-M and RP2040/RP2350 microcontrollers, with real build commands.",
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

**Is Forth worth learning in 2026?**
Yes, if you work close to hardware or care about tiny runtimes. It is also one of the few languages where a single person can read the entire specification and hold the whole system model in their head. Its practical niche is embedded control, bootstrapping, interactive hardware bring-up, and teaching how a stack machine actually executes. It is a poor choice for large application development with many contributors.

**What is the difference between Gforth, pForth, and zeptoforth in one sentence each?**
Gforth is the GNU implementation for POSIX workstations and the best place to learn the language. pForth is a small portable C Forth kernel meant to be embedded inside other software and cross-compiled to odd CPUs. zeptoforth is a multitasking Forth system for ARM Cortex-M and RP2040/RP2350 microcontrollers with a live serial console.

**Can I use Forth for a production embedded product?**
Yes — Forth has shipped in production firmware for decades, including space and instrumentation systems. The requirements are discipline: pin your toolchain, keep a conformance test in CI (pForth ships coretest, use it), document your words, and remember that a live REPL in production firmware is a security decision, not just a convenience.

**How do I get started on a Raspberry Pi Pico?**
Flash a zeptoforth UF2 image by holding BOOTSEL while plugging in the board, then copy the kernel `.uf2` to the mounted volume. Open the zeptocom.js web terminal, connect at 115200 baud, and start typing Forth. You do not need to build anything from source for a first session.

**Why does my Forth code work on my laptop but fail on the microcontroller?**
Almost always cell size or an extension word. A 64-bit host gives you 64-bit cells; the board gives you 32. Check every use of `@`, `!`, and double-cell arithmetic, replace raw byte offsets with `cells` and `cell+`, and verify each unfamiliar word against the target's documentation rather than the host's.

**Do these implementations talk to each other's code?**
Reasonably well if you stay inside the standard core. Conformance suites such as coretest exist precisely to keep implementations honest. Practically, expect to adapt code for extension words, floating point, and multitasking, because those areas are where implementations legitimately diverge.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
