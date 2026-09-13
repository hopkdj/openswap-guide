---
title: "The Definitive Guide to the Zig Toolchain in 2026: zig build, ZLS, and zig cc Compared"
date: "2026-09-14"
description: "zig build vs Make vs CMake, ZLS language server setup, and zig cc as a universal C cross-compiler — a hands-on 2026 guide with real build.zig, build.zig.zon, and zls.json configs."
tags: ["zig", "build-systems", "cross-compilation", "developer-tooling", "compilers"]
draft: false
cover: "/img/screenshots/zig-logo-dark.jpg"
---

Here is the fact that should get your attention: **`zig cc` is a fully working C and C++ cross-compiler for 12+ targets, and it ships inside a single ~45 MB tarball with zero external dependencies.** No `gcc-riscv64-linux-gnu` package. No sysroot tarballs. No Docker image full of cross toolchains. You download Zig, and thirty seconds later you are producing static RISC-V binaries on an x86 host.

The Zig project's compiler repo passed **43,310 stars** before it moved to Codeberg, and the surrounding toolchain — the `zig build` system and the ZLS language server at **5,127 stars** — is now mature enough to replace Make, CMake, and your cross-compilation setup on real projects. This guide covers all three components, with configuration pulled from the official repos rather than written from memory, and tells you plainly which parts are ready and which will still bite you.

## TL;DR — The Quick Verdict

**Use `zig build` if you are starting a new systems project or you are tired of CMake's `CMakeLists.txt` verbosity** — the build script is ordinary Zig code, and cross-compilation is one flag. **Add ZLS immediately if you write Zig in any editor**; it is MIT-licensed and trivial to install, but you must pin it to Zig 0.16.0 today because its build-system integration with Zig nightly is known-broken. **Use `zig cc` even if you never write a line of Zig** — this is the single highest-value part of the toolchain for most teams, because it turns C cross-compilation from a week-long yak shave into a one-line command.

The honest summary: `zig cc` is production-ready and you should adopt it today. `zig build` is production-ready for new projects and painful for anything with heavyweight existing build requirements. ZLS is excellent but chained to Zig's release cadence.

## The Three Components Compared

All stars, release versions, and dates below were pulled from GitHub and ziglang.org in September 2026.

| | `zig build` | ZLS | `zig cc` |
|---|---|---|---|
| **What it is** | Build system, part of the Zig compiler | Language server implementing LSP | C/C++ cross-compiler frontend |
| **Repository** | Codeberg (`ziglang/zig`), GitHub mirror at 43,310 stars | `zigtools/zls`, **5,127 stars** | Same as Zig compiler |
| **Written in** | Zig | Zig | Zig (drives LLVM) |
| **Latest stable** | **Zig 0.16.0** (previous stable 0.15.2; master at `0.17.0-dev.2127`) | **0.16.0**, released Apr 2026 | Ships with Zig |
| **Last activity** | Sept 2026 (dev branch) | **Sept 11, 2026** | Sept 2026 |
| **License** | MIT | MIT | MIT |
| **Install cost** | Included with the compiler | One binary (`zig build -Doptimize=ReleaseSafe`) | Included with the compiler |
| **Learn-with-your-existing-skills** | Requires learning Zig syntax | None — standard LSP | None — `gcc`-compatible flags |
| **Best for** | New projects, cross-compilation, hermetic builds | Editing, navigation, diagnostics | Shipping C/C++ to non-native targets |

The stability picture matters more than the feature list. **`zig cc` is the most stable of the three** because its interface is a familiar compiler CLI. **`zig build` changes API between minor versions** — the `Build` API has been reworked across 0.13 → 0.15. **ZLS tracks Zig so tightly that its own README tells you not to use it against Zig master.**

## Decision Matrix: Pick Your Component in 10 Seconds

| Your situation | Component | Why |
|---|---|---|
| C project needs to ship Linux ARM64 + x86_64 + musl | **`zig cc`** | One tool, all targets, static musl binaries |
| Tired of maintaining `CMakeLists.txt` + Ninja + pkg-config | **`zig build` + `zig cc`** | One `build.zig`, one dependency system |
| Editor has no Zig completion or go-to-definition | **ZLS** | Full LSP: completions, hover, rename, inlay hints |
| Building a Go or Rust project | **Neither** | Use the native toolchain; this stack is C/C++/Zig oriented |
| Monorepo with Bazel or Nx already working | **`zig cc` only** | Keep the build graph, replace the compiler |
| Need cross-compiled static binaries in CI | **`zig cc` in a container** | ~45 MB image, no apt cross packages |
| Building a static site or docs after build | **Zine** (also Zig) | Compiles content into a static site from Zig |
| Distributing a Zig library to other projects | **`build.zig.zon`** | Built-in package manifest with content hashes |

## `zig build` — A Build System That Is Just Code

The pitch for `zig build` is that your build script is an ordinary Zig program. There is no separate DSL to learn, no `Makefile` tab-vs-space archaeology, and no autoconf regeneration step. The entry point is the `build` function, and the official `zig init` template documents the API's intent precisely: the function "does not perform the build directly and instead mutates the build graph (`b`) that will be then executed by an external runner."

Here is the standard target and optimization setup from the official template:

```zig
const std = @import("std");

pub fn build(b: *std.Build) void {
    // Standard target options: any target allowed, default is native.
    const target = b.standardTargetOptions(.{});

    // Debug, ReleaseSafe, ReleaseFast, ReleaseSmall — chosen by the caller.
    const optimize = b.standardOptimizeOption(.{});

    // Custom flags show up in `zig build --help`.
    const single_threaded = b.option(bool, "single-threaded", "Build single threaded");
}
```

Any flag you declare through `b.option()` is automatically documented in `zig build --help`, which means your build script is self-documenting. That is a genuinely nicer property than a `Makefile` full of undocumented variables.

For a real executable, `zig build` exposes the install and run steps the same way every Zig project does. The convention is worth internalizing because every Zig repository you clone behaves identically:

```bash
# The four commands that work in every Zig project
zig build                          # debug build
zig build -Doptimize=ReleaseFast   # optimized build
zig build run                      # build and execute
zig build test                     # run unit tests

# Cross-compile without a cross toolchain installed
zig build -Dtarget=x86_64-linux-musl
zig build -Dtarget=aarch64-linux-gnu
zig build -Dtarget=riscv64-linux-musl
```

That last group is the killer feature. `-Dtarget=` is not a special Zig project setting — it comes free from `b.standardTargetOptions(.{})`. The moment you call that function in your `build.zig`, your project becomes cross-compilable to any target Zig supports, which is an unusually long list. ZLS's own `build.zig` enumerates release targets across `aarch64`, `arm`, `loongarch64`, `riscv64`, `x86`, `x86_64`, `powerpc64le`, `s390x`, and `wasm32-wasi` — that list is a fair proxy for what the compiler targets in practice.

### Dependency management via `build.zig.zon`

Zig's package manifest is `build.zig.zon`, and its format is refreshingly blunt: name, version, minimum compiler version, and a dependency table where each entry carries a URL and a content hash. Here is the real structure, from ZLS's manifest:

```zig
.{
    .name = .zls,
    .version = "0.17.0-dev",
    // Minimum Zig version required to compile and test this package.
    .minimum_zig_version = "0.17.0-dev.1936+5a625d5f3",
    .dependencies = .{
        .known_folders = .{
            .url = "https://github.com/ziglibs/known-folders/archive/<commit-sha>.tar.gz",
            .hash = "known_folders-0.0.0-Fy-PJiDLAAB98m3uYUzatrTb2mO2fpvwx2zpSroEtfbO",
        },
    },
}
```

Two things are worth noticing. First, **`.minimum_zig_version` is declared and enforced** — a package can refuse to build against the wrong compiler, which kills an entire class of confusing errors. Second, **dependencies are content-addressed by hash**, so a tarball URL that silently changes content fails the build. You get lockfile-grade reproducibility without a lockfile.

You can also import the manifest from the build script itself. Zine, the Zig static site generator, does exactly this:

```zig
const zon = @import("build.zig.zon");
const std = @import("std");
// zon.version is available as a compile-time value
```

**Where `zig build` falls down:** C and C++ projects with heavy existing build requirements. If a dependency only ships a broken `configure` script or expects pkg-config quirks, you will be writing that logic yourself in Zig. The ecosystem's answer is `zig cc` — use Zig's compiler with the build system you already have.

## ZLS — Editor Intelligence, With a Version Pin

ZLS is a **non-official implementation of the Language Server Protocol for Zig, written in Zig**, and it is MIT-licensed. It supports the LSP features you actually use daily, per its README:

- Completions, hover, and signature help
- Diagnostics and opt-in **build-on-save**
- Go to definition and declaration
- Workspace symbols and document symbols
- Find references and rename symbol
- Formatting based on `zig fmt`
- Semantic token highlighting and inlay hints
- Code actions

![ZLS — the Zig language server, official project logo](/img/screenshots/zig-zls-language-server-logo.jpg "ZLS Zig language server project logo")

Building from source is three commands, straight from the README:

```bash
git clone https://github.com/zigtools/zls
cd zls
zig build -Doptimize=ReleaseSafe
```

**Now the warning that the project publishes in a callout box, because it is the most common way people break their setup:**

> ZLS currently lacks critical build system integration with Zig nightly/master. It is recommended to use Zig and ZLS **0.16.0** in the meantime.

The project's own `build.zig` carries a `minimum_runtime_zig_version` constant pinned to a specific nightly build string, which tells you the compatibility window is narrow and enforced deliberately. **Pin both sides and upgrade them together.** The README's instruction is explicit: when upgrading Zig, update ZLS too, to keep them in sync.

### Configuring ZLS

ZLS reads a `zls.json` config file, and the repo ships a full JSON Schema for it. The keys below are taken directly from that schema — descriptions included, because they explain non-obvious trade-offs:

```json
{
  "enable_snippets": true,
  "enable_argument_placeholders": true,
  "completion_label_details": true,
  "enable_build_on_save": true,
  "build_on_save_args": [],
  "semantic_tokens": "partial"
}
```

- **`enable_build_on_save`** — enables build-on-save diagnostics. The schema notes it "will be automatically enabled if the `build.zig` has declared a 'check' step." This is the single most valuable ZLS setting: your editor reports real compiler diagnostics, not just syntax parsing.
- **`build_on_save_args`** — arguments passed to Zig during build-on-save. If your `build.zig` declares a `check` step, ZLS prefers it over the default `install` step.
- **`completion_label_details`** — shows function signatures in completion results; disable it if your completion popup feels noisy.
- **`semantic_tokens`** — `none`, `partial`, or `full`. The schema describes `partial` as including "only information that requires semantic analysis," which is the sensible default since syntax-only highlighting is already handled editor-side.

For editor-specific wiring, binary downloads, and per-editor configuration, the project maintains a complete installation guide on the Zigtools website (`zigtools.org/zls/install/`).

## `zig cc` — The Part You Should Adopt Today

`zig cc` is a drop-in C compiler that piggybacks on Zig's bundled LLVM, linker, and C library set. It accepts `gcc`-shaped flags, and it can target glibc and musl across architectures **without any system cross packages installed**.

```bash
# Cross-compile a C program to four targets with zero extra packages
zig cc -target x86_64-linux-musl   -O2 -static -o app-x86_64  app.c
zig cc -target aarch64-linux-musl  -O2 -static -o app-arm64   app.c
zig cc -target riscv64-linux-musl  -O2 -static -o app-riscv64 app.c
zig cc -target x86_64-windows-gnu  -O2          -o app.exe     app.c

# C++ works the same way
zig c++ -target aarch64-linux-gnu -O2 -o libfoo.so foo.cpp
```

Why this matters for anyone who has maintained a build farm: the traditional approach requires a cross-compiler per architecture (`gcc-riscv64-linux-gnu`, `gcc-aarch64-linux-gnu`), plus a matching sysroot, plus careful glibc version pinning to avoid shipping binaries that need a newer libc than the target has. Zig packages a known-good glibc version matrix and lets you select it:

```bash
# Target an older glibc for maximum compatibility
zig cc -target x86_64-linux-gnu.2.17 -O2 -o app app.c

# Produce a fully static musl binary that runs anywhere
zig cc -target x86_64-linux-musl -static -O2 -o app app.c
```

And in CI, the tarball is the entire toolchain. There is no `apt install gcc-<arch>-linux-gnu` step, no multi-stage sysroot copying, and the image stays small:

```dockerfile
FROM debian:bookworm-slim
ARG ZIG_VERSION=0.16.0
RUN apt-get update && apt-get install -y --no-install-recommends curl xz-utils ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -sL "https://ziglang.org/download/${ZIG_VERSION}/zig-linux-x86_64-${ZIG_VERSION}.tar.xz" \
       | tar -xJ -C /opt \
    && ln -s "/opt/zig-linux-x86_64-${ZIG_VERSION}/zig" /usr/local/bin/zig
WORKDIR /src
RUN zig cc -target x86_64-linux-musl -static -O2 -o /out/app app.c
```

**Where `zig cc` falls down:** it is a C/C++ compiler, not a C/C++ ecosystem. It does not replace your linker flags knowledge, it will not fix a dependency that assumes autotools, and C++ standard library support via `zig c++` is good but not identical to a matching GCC/Clang version. Test your actual build before migrating a critical project.

## Zig for Infrastructure: Zine and Ziggy

Two adjacent tools round out the toolchain, and both matter if you run your own infrastructure.

| Project | Stars | What it is |
|---|---|---|
| `kristoff-it/zine` | **1,567** | Static site generator written in Zig; uses `zine.ziggy` for site config |
| `kristoff-it/ziggy` | 586 | Data serialization and package-manifest format used by Zine |
| `spiraldb/ziggy-pydust` | **787** | Build bridge that compiles Zig into Python extension modules |

**Zine** is worth a look if you self-host a documentation or marketing site. Its `build.zig` imports the manifest as a compile-time value and exposes its own module API for build assets with explicit `install_path` and `install_always` fields — meaning assets are only installed when something actually links them. It was last updated in September 2026 and is actively maintained.

**ziggy-pydust** is the more interesting one for real workloads: it lets you write performance-critical Python extension modules in Zig and build them through the standard Python packaging flow. If you already self-host Python services and hot paths are the bottleneck, this replaces writing C extensions with hand-rolled setup machinery.

## Pitfalls and Migration Gotchas

**1. Zig's build API changes between minor versions.** The `Build` API has been reworked repeatedly. Code written for Zig 0.13 will not compile on 0.15 without edits. Pin the compiler version in CI and in `build.zig.zon`'s `.minimum_zig_version`, and budget time for upgrades rather than assuming they are drop-in.

**2. ZLS and Zig nightly are a known-broken pairing.** The ZLS README says it outright: build system integration with Zig master is not working. Use **Zig + ZLS 0.16.0** as a matched pair. The moment you upgrade one, upgrade the other.

**3. The GitHub repo is a mirror — the project lives on Codeberg.** `ziglang/zig` on GitHub now reports "Moved to Codeberg." Any automation that watches, clones, or pins the GitHub repository is watching a stale mirror. Point your tooling at Codeberg, or pin Zig by release tarball URL from `ziglang.org/download/`.

**4. `build.zig.zon` hashes are not optional and not auto-filled.** Dependencies need a correct content hash. Get it wrong and the build fails; the compiler tells you the correct hash to paste, but this trips up everyone the first time they add a dependency by hand.

**5. Always name an explicit target when shipping binaries.** Omitting `-target` gives you a native build tuned to your build host's CPU and glibc. That binary will often segfault or fail to start on a different machine. `x86_64-linux-musl` with `-static` is the safe default for distribution.

**6. Zig's tarball is per-architecture.** Zig is distributed as `zig-linux-x86_64-<version>.tar.xz`, and there is a separate ARM64 download. In a multi-arch CI matrix, download the matching tarball per runner rather than assuming the x86_64 one works.

**7. Do not assume C++ parity.** `zig c++` handles a great deal, but C++ standard library and ABI details can differ from a matching system compiler. Build and test your real sources before you retire an existing toolchain.

For broader context on open build systems, our [Bazel vs Pants vs Please comparison](../2026-04-29-bazel-vs-pants-vs-please-self-hosted-build-systems-guide-2026/) covers the hermetic-build argument, our [monorepo build tools guide](../2026-06-16-self-hosted-monorepo-build-systems-nx-turborepo-bazel/) explains when a full build graph is worth it, and if you are still deciding on the language itself, our [Zig vs Rust vs Go breakdown](../2026-09-02-zig-vs-rust-vs-go-systems-programming-guide/) covers that decision.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "The Definitive Guide to the Zig Toolchain in 2026: zig build, ZLS, and zig cc Compared",
  "description": "A hands-on 2026 guide to the Zig toolchain: the zig build system, ZLS language server configuration, and zig cc as a universal C and C++ cross-compiler, with real build.zig, build.zig.zon, and zls.json examples.",
  "datePublished": "2026-09-14",
  "dateModified": "2026-09-14",
  "keywords": "Zig toolchain, zig build, ZLS, zig cc, cross-compilation, build systems, self-hosted developer tooling",
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

### Is `zig cc` a real replacement for GCC or Clang?

Yes for cross-compilation, and that is where it wins decisively. `zig cc` is a C compiler frontend driving LLVM, it accepts `gcc`-shaped flags, and it ships the linker, headers, and C library for every target it supports — so you can build for RISC-V, ARM64, and musl x86_64 from one machine with no cross packages installed. It is not a byte-for-byte replacement for a specific GCC version's semantics or its full set of extensions. For distribution builds, embedded targets, and CI cross-compilation, it is production-ready and simpler than any alternative.

### Do I need to write Zig to benefit from the Zig toolchain?

No. `zig cc` and `zig c++` work on existing C and C++ codebases with a one-word command change. This is the most common adoption path: teams keep their existing build system and swap the compiler. You only touch Zig syntax if you adopt `zig build` or if you start writing application code.

### Why does the Zig GitHub repository say "Moved to Codeberg"?

The project relocated primary development to Codeberg, and the GitHub repository is now a mirror. Practical consequences: the GitHub mirror lags, and any monitoring or dependency pinned to the GitHub repository is watching stale content. Install Zig from the official tarballs at `ziglang.org/download/`, and pin by exact version rather than tracking a branch.

### Which Zig and ZLS versions should I pair in 2026?

Pair **Zig 0.16.0** with **ZLS 0.16.0** — both the current stable releases, and the exact pairing the ZLS README recommends. The README explicitly warns that build system integration with Zig nightly/master is currently broken, and ZLS's `build.zig` pins a `minimum_runtime_zig_version` nightly string, so the compatibility window is narrow and intentional. Upgrade both together, never one in isolation.

### Can I use `zig build` in a monorepo that already uses Make or CMake?

Partially, and the sane pattern is to use both. Keep your existing build system for the parts that already work, and use `zig cc` as the compiler so you get cross-compilation for free. Migrate individual targets to `zig build` only when you are starting them fresh or when their existing build logic is the thing that keeps breaking. Rewriting a working build system in Zig is rarely the highest-value use of your time.

### What is the smallest possible cross-compilation container for a C project?

A Debian slim base plus the Zig tarball and nothing else. Because Zig bundles the linker, headers, and libc for each target, you do not install `gcc-<arch>-linux-gnu` or sysroot packages. The resulting image is roughly the size of the base image plus the Zig archive, and it can produce static binaries for every architecture Zig supports — which is a large reduction from the traditional multi-package cross toolchain image.

### Does the Zig toolchain work for building static binaries without glibc dependencies?

Yes — target musl and link statically, which is the standard recommendation for distribution. `zig cc -target x86_64-linux-musl -static -O2` produces a binary with no dynamic libc requirement at all. If you must ship against glibc instead, Zig lets you select the exact glibc version you target, such as `-target x86_64-linux-gnu.2.17`, which removes the usual "built against a newer libc than the target host has" failure mode.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
