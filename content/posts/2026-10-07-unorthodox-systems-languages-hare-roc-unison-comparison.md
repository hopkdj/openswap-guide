---
title: "Hare vs Roc vs Unison in 2026: 3 Unorthodox Languages That Rethink Systems Programming"
date: "2026-10-07"
tags: ["programming-languages", "systems-programming", "developer-tools", "compilers", "functional-programming"]
draft: false
cover: "/img/screenshots/hare-mascot.jpg"
description: "Hare, Roc and Unison each throw out an assumption the rest of the industry treats as sacred. Here is what they do differently, what they cost you, and which one deserves a weekend of your time."
---

The Rust-versus-Go argument has been running for a decade, and both camps have stopped listening. Meanwhile, three smaller languages are quietly attacking the parts of systems programming nobody else wants to touch: Hare deletes your runtime and your dependency manager, Roc deletes null and the class of bugs that comes with it, and Unison deletes build artifacts entirely by making source code content-addressed.

None of them is ready to replace your production stack tomorrow. All three are genuinely interesting, and one of them may be the right tool for a specific job you have right now. **This guide compares them using live repository data, real installation commands, and code you can compile today.**

## TL;DR: Quick Verdict

- **Choose Hare** if you write Linux/BSD system tools and want C-level control with a cleaner type system and a toolchain that fits in your head. It is a 0.x language with a small ecosystem, so treat it like a sharper C, not a Rust replacement.
- **Choose Roc** if you want functional programming that compiles to fast native binaries and you are comfortable with a single-package (`platform`) model where host code is written in Rust/Zig. Nightly-quality, rolling releases, brilliant ideas.
- **Choose Unison** if your problem is distributed systems or dependency hell: content-addressed code means no lockfile conflicts, no rebuild step, and unlimited free refactorings. The trade-off is that you work inside `ucm`, not in your editor's file tree.
- **Stay on Rust/Go** if you need hiring pools, mature crates, and stable release channels this quarter.

## Side-by-Side Comparison (Live Data, October 2026)

| Dimension | Hare | Roc | Unison |
|---|---|---|---|
| Paradigm | Imperative, systems-oriented | Purely functional, expression-based | Functional, content-addressed |
| Memory management | Manual, no hidden allocation | Garbage-collected + reference counting | Immutable, managed by the runtime (UCM) |
| Repository | `git.sr.ht/~sircmpwn/hare` (SourceHut) | `roc-lang/roc` — **6,098★** | `unisonweb/unison` — **6,743★** |
| Latest release | **0.26.0** (Feb 13, 2026) | `alpha4-rolling` (Aug 2026) + nightly builds | **release/1.5.0** (Oct 2, 2026) |
| Last repository activity | Active 0.x development cycle | Last push **Oct 7, 2026** | Last push **Oct 5, 2026** |
| Dependency model | System packages, vendored tree | Single `platform` URL per app | Codebase — hashes, not versions |
| Real build step | `hare build` | `roc build` (JIT by default) | None — `ucm` stores definitions |
| Package ecosystem | Small, curated, std + extended libs | Small but growing (basic-cli 0.21.0-rc4) | Unison Share library as a database |
| Supported platforms | Linux, FreeBSD, OpenBSD, NetBSD, DragonFlyBSD | Linux, macOS, Windows | Linux, macOS, Windows |
| License | MPL-2.0 | UPL-1.0 | MIT |
| Learning curve | Shallow for C programmers | Steep if you have never written FP | Steepest — new workflow, not just syntax |

## Decision Matrix: Pick in Ten Seconds

| Your use case | Pick | Why |
|---|---|---|
| Rewriting a small C daemon or CLI tool | **Hare** | Minimal runtime, C ABI interop, predictable memory |
| A networking utility that must not allocate unexpectedly | **Hare** | Manual memory management, no GC pauses by design |
| A data-transformation CLI with lots of parsing | **Roc** | Pattern matching, `Result`-style error handling, fast native output |
| Prototyping a compiler or interpreter | **Roc** | Algebraic data types and exhaustive matching make AST work pleasant |
| A distributed service where clients and servers must not drift | **Unison** | Content-addressed code makes cross-version calls safe |
| A codebase where every refactor causes merge pain | **Unison** | Renames are metadata operations, not file rewrites |
| Anything with a hiring requirement | **Rust or Go** | Talent pool and library coverage both still lead |

## Hare: The Smallest Language Here, On Purpose

![The Hare programming language mascot](/img/screenshots/hare-mascot.jpg "Hare programming language mascot from the official harelang.org site")

Hare is the language Drew DeVault built for the software he was already writing in C. It has a static type system with generics, manual memory management, and a deliberately tiny runtime — the project describes itself as suited to operating systems, system tools, compilers, and networking software. There is no garbage collector to tune and no async runtime to debug.

It is also the only one of the three that ignores the package-manager arms race entirely. The recommended installation path is your operating system's package manager under the name `hare`, which on Alpine looks like this:

```bash
# Alpine Linux (Hare is in the main repositories)
apk add hare

# Other distributions: bootstrap from source
# see https://harelang.org/documentation/install/ for the current procedure
git clone https://git.sr.ht/~sircmpwn/hare
cd hare
./configure
make
make install
```

The toolchain is one executable with subcommands, which keeps the mental model small:

```bash
hare build main.ha      # compile to an executable
hare run main.ha        # compile and execute
hare test               # run tests across the current module
haredoc fmt             # read the standard library docs offline
```

Here is the standard "greet the current user" program from the official documentation — note how errors propagate with `!` instead of being silently ignored:

```hare
use fmt;
use os;

export fn main() void = {
	const user = os::getenv("USER") as str;
	fmt::printfln("Welcome to the Hare documentation, {}!", user)!;
};
```

**What you get:** a language you can fully understand in an afternoon, native binaries with no runtime dependency, and a release cadence that has reached 0.26.0 (announced February 13, 2026) with support for Linux and all four major BSDs on x86_64, aarch64, and riscv64.

**What it costs you:** the ecosystem is tiny and the language is still pre-1.0, so annotation and API details can shift between releases. macOS has only third-party support, Windows is not planned. If you cannot run your production system on Linux or a BSD, Hare is a non-starter.

## Roc: Functional Programming That Compiles to Fast Binaries

Roc is what happens when someone keeps the good parts of Elm — exhaustive pattern matching, no null, errors as values — and drops the browser. It is written to produce small, fast native executables, with a Rust/Zig "host" providing platform primitives while your application code stays purely functional.

The architecture you must understand before writing a line of Roc is *platforms*. An application declares the platform it runs on as a URL with a cryptographic hash, and that URL determines what capabilities exist:

```roc
app [main!] { pf: platform "https://github.com/roc-lang/basic-cli/releases/download/0.21.0-rc4/FvCh4vdqm3nBY6DWEfZ8RuGCVfjuMY43HA8KSNk9qVDn.tar.zst" }
```

That single line replaces what other ecosystems express as a manifest, a lockfile, a compiler configuration, and a build script. The most common target is `basic-cli`, currently at 0.21.0-rc4, which supplies file, HTTP, JSON, and stdin/stdout primitives.

Roc code itself is expression-oriented and reads like a pipeline. This is a real snippet of the style the project uses on its homepage for list transformation:

```roc
print_remaining! = |todos|
    todos
    .keep_if(|todo| todo.status != Done)
    .for_each!(|todo| echo!("- ${todo.name}\n"))

main! = |_args| {
    todos = [
        { name: "Learn Roc", status: Done },
        { name: "Buy groceries", status: Done },
        { name: "Write blog post", status: InProgress },
    ]
    print_remaining!(todos)
    Ok({})
}
```

There is no `null` anywhere in the language and no unchecked exception path — failures travel through the type system, and the compiler refuses to proceed when a match is incomplete.

Installation is a rolling-nightly affair. The stable-tagged release is `alpha4-rolling`, and the practical way to get a working compiler today is the nightly bundle:

```bash
# Linux x86_64 nightly (also: macos, windows, aarch64 builds are published)
curl -LO https://github.com/roc-lang/roc/releases/download/nightly/roc_nightly-linux_x86_64-latest.tar.gz
tar -xzf roc_nightly-linux_x86_64-latest.tar.gz
./roc version

# Run a program directly (Roc JITs by default)
./roc run main.roc

# Build a native binary
./roc build main.roc
```

**What you get:** the strongest type-driven refactoring story of the three, a pleasant pipeline syntax, and genuinely fast output thanks to LLVM behind the scenes. The repository was still being pushed the morning this article was written — **6,098 stars and activity on October 7, 2026** — so the project is very much alive.

**What it costs you:** it is alpha software with rolling releases. The platform model means you cannot pull an arbitrary library; if a capability does not exist in your platform, you (or someone else) must write it in the host language. Editor tooling is improving but lags Rust's.

## Unison: Code With No Build Step at All

Unison is the most radical of the three, because it changes not the syntax of programming but the storage format of programs. Definitions are stored inside a **codebase** keyed by the hash of their own content. There are no source files in the usual sense, no build step, and no dependency version conflicts: if a function's dependencies change, its hash changes, and both versions coexist.

You install the codebase manager (`ucm`) from the official release archive — release/1.5.0 landed on **October 2, 2026**:

```bash
# Linux x64 — the official installer archive from GitHub releases
curl -L https://github.com/unisonweb/unison/releases/latest/download/ucm-linux-x64.tar.gz \
  | tar -xz
./ucm

# On macOS with Homebrew
brew install unison-language
```

Inside `ucm` you work in a Hazel-style scratch file, and every definition you save is hashed and pushed into the codebase:

```text
.> pull https://github.com/unisonweb/share:.base
.> view List.map
.> add myProject.main
.> run myProject.main
```

The practical payoff is what Unison calls unlimited free refactorings: renaming a function or changing its argument order rewrites every call site in the codebase because the tooling knows the dependency graph. Abilities (typed effects) are first-class, which makes it possible to write code that is agnostic about whether it is running locally or against `IO` in a distributed setting.

**What you get:** independence from lockfiles and build pipelines, a library system where dependency upgrades are never forced, and a coherent story for distributed execution. The repository has **6,743 stars** and was last pushed on October 5, 2026.

**What it costs you:** you must adopt a new workflow. The codebase lives in `ucm`, not in a `src/` directory you can `grep`. Git-based review workflows are awkward by comparison, and the community, while enthusiastic, is small.

## Pitfalls Before You Commit a Weekend

1. **Do not judge them by GitHub stars alone.** Roc and Unison have healthy star counts but ecosystems measured in dozens of libraries, not thousands. Count the packages you actually need before you commit a project.
2. **Hare's pre-1.0 status is real.** Because the language targets stability of *design*, not of *interface*, you should expect annotation and library details to move between 0.x releases. Pin your toolchain version in CI.
3. **Roc's rolling releases break things.** The last tagged release is `alpha4-rolling`, and the platform URL in your app header embeds a hash — upgrading means updating that URL and re-testing. There is no `cargo update` equivalent, and that is deliberate.
4. **Unison is not a drop-in.** You cannot `import` your existing project into a codebase and keep editing files. Migration means rewriting the entry points inside `ucm`, and your CI pipeline needs `ucm transcript` rather than a compiler invocation.
5. **Cross-compilation is the weak spot for all three.** Hare supports only Linux and BSDs, Roc's platform hosts must exist for your target, and Unison's own runtime is what executes your code. If your deployment target is exotic, verify support before you write the first line.
6. **Memory behaviour differs more than benchmarks suggest.** Hare gives you control and the responsibility that comes with it; Roc and Unison manage memory for you and therefore have a runtime, which changes the failure modes you will debug at 3 a.m.

If you are weighing this decision against the mainstream options, our [Zig vs Rust vs Go systems programming guide](../2026-09-02-zig-vs-rust-vs-go-systems-programming-guide/) covers the stability-versus-velocity trade-off in the same terms, and the [V vs Go vs C comparison](../2026-10-04-vlang-vs-go-vs-c-systems-language-comparison/) examines what a smaller language must offer to be worth adopting. For a different escape hatch from conventional tooling, the [tiny C compilers comparison covering TCC, chibicc and cproc](../2026-09-24-tcc-vs-chibicc-vs-cproc-tiny-c-compilers/) shows how far minimalism can be pushed in the C world. And if your interest in Unison is really about functional ideas, our [Scheme implementations comparison](../2026-09-13-scheme-implementations-racket-chez-guile-comparison/) traces the lineage these designs came from.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Hare vs Roc vs Unison in 2026: 3 Unorthodox Languages That Rethink Systems Programming",
  "description": "Live-data comparison of Hare, Roc and Unison: paradigms, memory models, installation commands, real code samples and the pitfalls of adopting a pre-1.0 systems language in 2026.",
  "datePublished": "2026-10-07",
  "dateModified": "2026-10-07",
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

**Is Hare ready for production in 2026?**
For small, self-contained Linux or BSD utilities, yes — people ship Hare binaries. For anything requiring a large third-party ecosystem or a 1.0 stability promise, no. Treat the 0.x series as a real language with an unstable interface.

**How fast is Roc compared to Rust or Go?**
Roc compiles through LLVM and produces native binaries with performance in the same range as other LLVM-backed systems languages, but the fair comparison for your workload requires measurement, not vendor claims. Its differentiator is the type system and pipeline syntax, not raw speed.

**What problem does Unison actually solve?**
Dependency version conflicts and safe distributed execution. Because code is content-addressed, two versions of a dependency cannot collide, and a remote call always executes against the exact definition it was compiled with.

**Can I use these languages with my existing editor setup?**
Hare ships editor plugins for common editors and `haredoc` for offline documentation. Roc has a language server with improving coverage. Unison is the outlier: your primary editing interface is `ucm` itself, though there is editor integration for the scratch file workflow.

**Do any of them have a package manager like npm or Cargo?**
Hare relies on system packages and a vendored source tree. Roc resolves a single platform URL per application. Unison's equivalent is its codebase plus Unison Share, which behaves more like a library database than a package registry.

**Which one should a beginner learn first?**
None of them. Learn Rust or Go for employability, then come back to Roc if you enjoy functional programming or to Unison if you care about distributed systems. Hare is the easiest of the three to pick up *if* you already know C.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
