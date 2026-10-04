---
title: "mold vs LLVM lld vs GNU gold in 2026: Real Linker Benchmarks (and Why Your Build Is Slow)"
date: "2026-10-04"
tags: ["comparison", "guide", "self-hosted", "build-systems", "performance", "toolchain"]
draft: false
cover: "/img/screenshots/linker-benchmark-chrome.jpg"
---

Your C++ or Rust build spends a shocking fraction of its wall-clock time in a program you have probably never configured: the linker. Compilation is parallel and incremental-friendly; linking a 4 GiB debug binary is a single-pass, I/O-heavy, largely serial job that gets slower every time your binary grows — and modern binaries grow fast.

Linking Chromium's debug build with the traditional GNU toolchain takes **over 16 seconds on a 64-core Threadripper**. The same link with mold takes **1.65 seconds**. That is not a micro-optimization; it is a different edit-compile-debug loop.

This is a practical 2026 comparison of the three linkers that matter for Linux builds — **mold**, **LLVM lld**, and **GNU gold** — plus **wild**, the newcomer that is now beating both on some workloads. All performance numbers below come from the projects' own published benchmark suites, and all repository data was fetched live on 2026-10-04.

## The 60-Second Verdict (TL;DR)

- **Use mold by default.** It is the fastest of the established options in almost every published benchmark and it is a genuine drop-in replacement — one `-fuse-ld=mold` flag and your existing build system works. 17,292 stars, last commit 2026-10-04.
- **Use LLVM lld** if you are already in the LLVM toolchain world, need the broadest target support, or need a linker that is part of a vendor-supported compiler suite. 40,915 stars on the `llvm/llvm-project` monorepo, last commit 2026-10-04.
- **Stop choosing GNU gold.** gold was a genuine breakthrough when Google contributed it in 2008, and it is still in the binutils tree — but lld and mold both exist because gold's design hit a wall. It is the option you migrate away from.
- **Watch wild.** A Rust linker from David Lattimore, now at 4,011 stars with a commit pushed 2026-10-04. It is targeting incremental linking, it has real published benchmarks, and it is the only one of the four with a credible plan to make relinking near-free.

**If you only change one thing today: add `-fuse-ld=mold` to your build and measure.**

## Real Benchmark Numbers

The table below is reproduced from **mold's own benchmark suite (August 2026)**, published in the project README. The machine is an AMD Ryzen Threadripper 7980X (64 cores) running Ubuntu 24.04, all three linkers built from source in release configuration as of 2026-08-28, default options, median of three runs after a warm-up. Debug builds, so binaries are large.

| Program (output size) | lld | wild | mold | wild/mold | lld/mold |
|---|---|---|---|---|---|
| Blender 5.2 (2.46 GiB) | 4.72s | 1.98s | **0.86s** | 2.3x | **5.5x** |
| Chromium 145 (4.51 GiB) | 16.64s | 3.98s | **1.65s** | 2.4x | **10.1x** |
| Chromium 145 ARM64 (4.76 GiB) | 20.91s | N/A | **1.83s** | N/A | **11.4x** |
| Clang 21 (4.19 GiB) | 6.19s | 3.71s | **1.34s** | 2.8x | 4.6x |
| ClickHouse 26.1 (5.58 GiB) | 6.62s | 4.40s | **0.98s** | 4.5x | 6.7x |
| Firefox 149 (2.37 GiB) | 5.11s | N/A | **0.78s** | N/A | 6.5x |
| Godot 4.6 (1.01 GiB) | 1.77s | 1.08s | **0.46s** | 2.3x | 3.8x |
| LibreOffice 26.2 (0.98 GiB) | 3.46s | 1.41s | **0.44s** | 3.2x | 7.9x |
| PyTorch 2.9 (3.51 GiB) | 4.35s | 2.48s | **0.80s** | 3.1x | 5.4x |
| TensorFlow 2.21 (9.55 GiB) | 50.73s | N/A | **3.15s** | N/A | **16.1x** |

mold's summary headline: **4.9x faster than LLVM lld and 1.9x faster than wild at the median.** The wild project publishes its own, independent charts, and they tell a similar story from the other side. On wild's Ryzen 9 9955HX Chrome benchmark, lld 21.1.8 sits at roughly **5x** wild's link time and mold 2.41.0 at roughly **2x**, with wild 0.8.0–0.10.0 clustering near 1 second.

![Official wild linker benchmark chart showing Chrome link times for lld, mold, and successive wild releases on a Ryzen 9 9955HX](/img/screenshots/linker-benchmark-chrome.jpg "Wild linker project benchmark: Chrome link time by linker")

A second chart from the same repository, run on a 4-core 2020 laptop, is the more useful one for most developers — it shows what happens on hardware you might actually own:

![Official wild linker benchmark chart from a 4-core laptop, comparing link times across linkers](/img/screenshots/linker-benchmark-laptops.jpg "Wild linker benchmarks on a 4-core laptop")

The takeaway is consistent across hardware: **the linker choice is worth more than most people's build micro-optimizations.** If you have already tuned your build cache, this is the next lever — see our [sccache vs ccache vs Icecream build cache comparison](../2026-04-23-sccache-vs-ccache-vs-icecream-self-hosted-build-cache-2026/) for the layer above it.

## Decision Matrix: Which Linker for Which Project

| Your situation | Pick | Why |
|---|---|---|
| C/C++/Rust project on Linux, want it faster today | **mold** | Drop-in, fastest established option, one flag to switch |
| Using the LLVM/Clang toolchain end to end | **lld** | Same vendor, widest target coverage, already installed |
| Cross-compiling to many architectures | **lld** | mold covers the common targets; lld covers everything LLVM does |
| Huge monorepo where relinking dominates the loop | **wild** (evaluate) | Built for incremental linking; documented benchmarks |
| Android / Chrome / PlayStation-class platforms | **lld** | lld is what those platforms' production builds use |
| Legacy build scripts pinned to gold behaviour | Stay on gold **temporarily** | Then move to mold or lld; gold is the past |
| Need a commercial support contract | Vendor LLVM toolchain | Neither mold nor wild offers vendor support |

## mold: The Rust Linker That Rewrote the Rules

mold is the project that made linkers interesting again. Its author wrote the original LLVM lld, hit architectural limits while optimizing it, and started over from scratch in Rust. That history matters: mold is not a faster lld, it is a design that avoids the constraints lld was built around.

mold is a **drop-in replacement** for existing Unix linkers. In practice this means you do not edit your build system; you tell the compiler which linker driver to invoke.

```bash
# Debian / Ubuntu ship mold in the archive
sudo apt-get install mold

# Fedora / RHEL family
sudo dnf install mold
```

Then point GCC or Clang at it. Both the driver-flag form and the direct-link-driver form work:

```bash
# Let the compiler driver find mold (GCC 12+, Clang 12+)
gcc -fuse-ld=mold build.o -o app
clang -fuse-ld=mold build.o -o app

# Rust: pass it through the linker arguments
RUSTFLAGS="-C link-arg=-fuse-ld=mold" cargo build

# Or run mold exactly like the system ld
mold -o app build.o
```

If you built mold from source with the project's install script, it lands under `/usr/local` and you point GCC at its embedded search directory:

```bash
# mold's own build instructions: install then use the wrapper path
sudo ./install-mold.sh
gcc -B/usr/local/libexec/mold build.o -o app
```

mold supports x86-64, i386, ARM 32/64, RISC-V 32/64, PowerPC 32/64, s390x, LoongArch 32/64, SPARC64, m68k, and SH-4 — per the project README. It has been in production use since 2021 and is the default linker for a growing list of large projects.

**When to pick it:** you want the most speed for the least effort. If your build is LLVM-based and your targets are covered, mold is the default recommendation for 2026.

## LLVM lld: The Default You Probably Already Have

lld is the linker that ships with LLVM, and odds are good that it is already on your machine if you have any Clang-based toolchain installed. It is the linker used to build Android, Chrome, FreeBSD, and multiple console platforms, which makes it the most heavily exercised alternative linker in existence.

```bash
sudo apt-get install lld          # Debian / Ubuntu
sudo dnf install lld              # Fedora
```

```bash
# Use lld via the compiler driver
clang -fuse-ld=lld build.o -o app
gcc -fuse-ld=lld build.o -o app

# Jump straight to the linker itself
ld.lld -o app build.o
```

lld's advantages over mold are not speed — mold wins the published benchmarks pretty much across the board. They are **breadth and institutional weight**:

- **Target coverage.** lld supports far more architectures and object formats through the LLVM backend, which matters the moment you cross-compile or target something unusual.
- **Vendor support.** If you buy a toolchain contract, it will include lld. It will not include mold.
- **Debug tooling.** More of the ecosystem has been tested against lld's output, including some proprietary debuggers and profilers.
- **You already have it.** On many distributions lld is a `-fuse-ld` flag away with zero new packages.

**When to pick it:** cross-compilation at scale, LLVM-first toolchains, vendor-supported builds, or any project where "widest tested target support" beats "fastest on the targets you use".

## GNU gold: The Legacy Option You Are Migrating Away From

GNU gold deserves its place in the story. It was designed at Google by Ian Lance Taylor, contributed to the Free Software Foundation in March 2008, and it was the first serious attempt to make a linker that runs "as fast as possible on modern systems" rather than preserving decades of GNU ld behaviour. At the time, it was a dramatic improvement over bfd ld.

It is also, in 2026, no longer where the development energy is. The reasons are architectural and well documented:

- **gold is a compatibility-first design.** Its own README describes it as a drop-in replacement for the older GNU linker, and lists notable omissions it never adopted — MRI-compatible linker scripts and cross-reference reports (`--cref`) among them.
- **It is written in C++ inside the binutils tree**, which means its release cadence is tied to binutils rather than to linker work.
- **Both successors were built explicitly to escape it.** lld was designed as a modern rewrite, and mold then started over *again* to escape the limits found while optimizing lld.

Practical guidance: check whether you are actually using gold before you "migrate" anything, because plenty of distributions quietly defaulted to bfd ld or lld years ago.

```bash
# What is my compiler actually using?
gcc -print-prog-name=ld
ld --version | head -1

# Force a specific one for a single build
gcc -fuse-ld=gold build.o -o app
gcc -fuse-ld=bfd  build.o -o app
gcc -fuse-ld=lld  build.o -o app
gcc -fuse-ld=mold build.o -o app
```

If `-fuse-ld=gold` still resolves on your system, it exists for compatibility. There is no 2026 workload where choosing gold over mold or lld is the right engineering call.

## wild: The Newcomer Built for Incremental Linking

wild is the most interesting project in this space. It is a Rust linker by David Lattimore, and its stated goal is not "be fast at full links" but **"be fast for iterative development"** — the plan is incremental linking, so that a relink after editing one file stops scaling with the size of the whole output.

It is not there yet, and the README says so plainly: incremental linking "isn't yet implemented". What wild already has is a serious full-link implementation with published benchmarks and a fast release cadence — the charts above include wild 0.6.0 through 0.10.0, all measured, on real projects (Chrome, bevy-dylib, rust-analyzer, ripgrep, the rustc driver).

Install paths are as modern as the rest of the project:

```bash
# Homebrew
brew install wild-linker/wild/wild

# cargo-binstall
cargo binstall wild-linker

# Build from crates.io
cargo install --locked wild-linker
```

wild supports x86-64, AArch64, RISC-V (riscv64gc), LoongArch64, and initial PPC64LE support — all on Linux, with Mach-O, WebAssembly, and Windows on the roadmap. It also supports CREL relocations, a newer, more compact relocation format that Chrome uses by default.

**When to pick it:** you have a huge monorepo where you relink constantly, you are comfortable evaluating a younger project, and you want to be early on the feature that actually solves your problem. For a conservative production build, mold or lld today; for the interesting bet, wild.

If your build is orchestrated by a large-scale build system, the linker is one of several levers — our comparisons of [Bazel vs Pants vs Please](../2026-04-29-bazel-vs-pants-vs-please-self-hosted-build-systems-guide-2026/) and [Nx vs Turborepo vs Bazel for monorepos](../2026-06-16-self-hosted-monorepo-build-systems-nx-turborepo-bazel/) cover the layer above this one.

## Pitfalls: What Breaks When You Swap Linkers

1. **Your build script may hardcode `ld`.** CMake, autotools, and hand-rolled Makefiles sometimes invoke `ld` directly instead of going through the compiler driver. Look for `${LD}` or bare `ld` invocations before assuming `-fuse-ld` took effect. Verify with `ldd`/`readelf` on the output and check the link line with `make VERBOSE=1` or `cmake --build . --verbose`.
2. **Debug info formats differ in volume.** mold and lld produce different (usually better) debug info than bfd ld, but the resulting binaries can be dramatically larger or smaller. If your CI has artifact size limits, measure before switching.
3. **Unusual linker scripts can trip mold.** mold supports the common script directives, but hand-crafted embedded linker scripts are a known weak spot. Test on your exotic target before rolling out fleet-wide.
4. **Sanitizers and coverage flags assume a specific linker.** Some sanitizer runtimes need the compiler driver to drive linking. Keep `-fuse-ld` at the driver level rather than replacing `ld` in `PATH`.
5. **`-fuse-ld` silently ignored on old compilers.** GCC before 12 and Clang before 12 have inconsistent support. If the build time does not change, verify the flag was honored rather than assuming it was.
6. **Do not benchmark your first switch on a cold cache.** Link time is dominated by page cache and disk. Run a warm-up link first; every project's published methodology here does exactly that.
7. **ThinLTO and `--lto-*` flags are not portable between linkers.** Migrating a ThinLTO pipeline from lld to mold requires re-validating your LTO configuration. Treat it as a build change, not a flag change.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "mold vs LLVM lld vs GNU gold in 2026: Real Linker Benchmarks (and Why Your Build Is Slow)",
  "description": "2026 linker comparison for Linux builds: mold vs LLVM lld vs GNU gold, plus wild. Published benchmark tables, install commands, -fuse-ld configs, and migration pitfalls.",
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

### Is mold actually faster than lld, or is that just marketing?

It is measured, and the measurements are reproducible. mold's August 2026 suite links Chromium 145's debug build in 1.65s versus lld's 16.64s — a 10.1x difference — and reports a 4.9x median advantage across nine large programs. wild's independent benchmark charts show the same ordering, with lld roughly 5x slower than wild and mold about 2x slower than wild on Chrome. Different machines and programs shift the multiple; the direction does not.

### Can I just replace `ld` with mold and forget about it?

Usually yes, and that is the intended workflow — but do it at the compiler-driver level (`-fuse-ld=mold`), not by symlinking `ld`. Replacing `ld` globally in `PATH` will break build steps that expect bfd-specific behaviour, and it hides which linker is actually in use. If a project breaks, the driver flag makes it trivial to test `-fuse-ld=lld` side by side instead of debugging a swapped binary.

### Does lld have anything mold does not?

Breadth. lld covers more architectures and object formats through the LLVM backend, it is part of a toolchain you can buy support for, and it is the linker that builds Android and Chrome — meaning an enormous amount of the ecosystem has been tested against it. mold wins on speed; lld wins on target coverage and institutional trust. For pure Linux x86-64/AArch64 builds, speed usually matters more.

### Is GNU gold deprecated?

gold is still present in the binutils tree and still works, but it has been superseded on both sides: lld was written as a modern rewrite, and mold was then written from scratch to escape the limits found while optimizing lld. mold's author describes mold as free of "the architectural limits its author had run into while optimizing lld." Practically, gold is a compatibility option in 2026 — not a performance choice.

### What linker should I use for a large monorepo with slow incremental builds?

Start with mold and measure your relink times; it is a drop-in flag change and by far the cheapest experiment. If relinking is still dominated by full-link cost, evaluate wild — its roadmap is explicitly about incremental linking, which is the actual fix for that specific problem, though the feature is not yet implemented and you would be adopting a younger project.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
