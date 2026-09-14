---
title: "Ada and SPARK in 2026: Alire vs GNAT Studio vs gnatprove Compared"
date: "2026-09-14"
tags: ["ada", "spark", "formal-verification", "build-tools", "developer-tools", "static-analysis"]
draft: false
cover: "/img/screenshots/alire-logo.jpg"
---

Ada has an unfair reputation problem: engineers hear "safety-critical" and assume the language is slow, the tooling is locked behind expensive support contracts, and the compiler only exists on a vendor's laptop. That was true in 1995. In 2026 the entire Ada and SPARK toolchain is open source, installs in under ten minutes, and does something no mainstream language can match out of the box: it can mathematically prove your code will not raise a runtime error.

The catch is that "the Ada toolchain" is actually three separate tools with three different jobs, and most newcomers install the wrong one first. **Alire** manages dependencies and builds. **GNAT Studio** is the IDE. **gnatprove** is the SPARK verifier that turns your contracts into machine-checked proofs. This guide covers all three, with real commands pulled from the official repositories and live project data as of **September 14, 2026**.

## TL;DR: Quick Verdict

**If you only install one thing, install Alire** — it bootstraps the compiler, resolves dependencies, and runs `gnatprove` for you via a single crate dependency. Add **GNAT Studio** (or the Ada Language Server in VS Code) when you want refactoring, call graphs, and an integrated debugger. Reach for **gnatprove with SPARK mode** only when a defect would be catastrophic — avionics, medical dosing, cryptography, payment rails. Testing finds bugs; proving removes entire bug classes. The proof effort is real, but so is the payoff.

## The Three Layers of the 2026 Ada Toolchain

| Tool | What it actually solves | Repository | Stars | Last activity | License | Install path |
|---|---|---|---|---|---|---|
| **Alire** | Dependency + build manager (`alr`) | `alire-project/alire` | **411** | 2026-08-28 | Open source (GitHub) | Prebuilt binary from Releases, or build with `alr` itself |
| **GNAT Studio** | Full IDE: editor, builder, debugger, profiler | `AdaCore/gnatstudio` | **529** | 2026-09-11 | GPL build shipped in repo | AppImage / Flatpak manifests in `distrib/` |
| **gnatprove (SPARK 2014)** | Static proof of runtime-error freedom | `AdaCore/spark2014` | **327** | 2026-09-14 | Open source prover | `alr with gnatprove`, or standalone release bundle |
| **Ada Language Server** | VS Code / Neovim / Emacs integration | `AdaCore/ada_language_server` | **304** | 2026-09-12 | Open source | Release bundle, paired with the Ada & SPARK extension |

All four repositories were actively committed to within the last three weeks. This is not a dying ecosystem — the SPARK prover repository received a commit **the same day this article was written**.

## Which Tool Should You Actually Use?

| Your situation | Pick this | Why |
|---|---|---|
| Starting a new Ada project today | **Alire** | `alr init` gives you a buildable, testable project tree in one command |
| Maintaining an existing GPR-based codebase | **Alire + GNAT Studio** | Studio reads `.gpr` files directly; Alire pins toolchain versions in `alire.toml` |
| Writing firmware for a Cortex-M target | **Alire + `gnat_arm_elf` toolchain** | Cross toolchains are published as index crates, not manual tarballs |
| Safety case required (DO-178C, EN 50128) | **gnatprove at level 2+** | Proof artifacts replace an unbounded pile of dynamic tests |
| You live in VS Code and hate heavy IDEs | **Ada Language Server** | Same compiler intelligence, zero IDE lock-in |
| Cryptography or parsing untrusted input | **SPARK subset + gnatprove** | Contracts on array bounds prove buffer overflows impossible |

## Alire: The Package Manager That Fixed Ada's Worst Problem

For thirty years, Ada's onboarding story was "download a toolchain from a vendor, hope the version matches your teammate's, and wire dependencies by hand." Alire ends that. It is a package manager, a build front end, and a toolchain installer rolled into a single binary called `alr`.

The project ships prebuilt binaries on its Releases page; the repository itself builds with `alr build`, which tells you how self-hosting the ecosystem has become.

```bash
# 1. Grab the latest stable alr binary from the Releases page, then:
alr version            # prints version + diagnostics for your platform

# 2. Create a project (binary executable, not a library)
alr init --bin fuel_monitor
cd fuel_monitor

# 3. Add dependencies from the community index
alr with gnatcoll           # AdaCore's general-purpose library collection
alr with gnatprove          # SPARK prover, wired into the same project

# 4. Build, run, and drop into a shell with the environment set
alr build
alr run
alr exec -- gnatprove -P fuel_monitor.gpr --level=1 --report=all
```

Three things make this more than a convenience wrapper. First, **`alire.toml` pins exact versions**, so a 2029 build machine reproduces a 2026 build exactly. Second, the **community index is generated from source manifests** — installing `gnat_arm_elf` or `gnat_riscv64_elf` pulls a real cross toolchain rather than asking you to compile GCC for a new target. Third, quality crates are one line away: `gnatcoll`, `gnattest` for test harness generation, `gnatcov` for coverage analysis, and `gnatformat` for formatting.

The honest limitation: the index is curated and community-maintained, so exotic libraries may still need a manual `externals` entry. For mainstream work — web services, embedded firmware, cryptography, parsers — coverage is good enough that you will rarely drop to hand-written build settings.

## GNAT Studio and the Editor Question

GNAT Studio is AdaCore's IDE: project browser, semantic-aware editor, integrated `gprbuild`, GDB front end, profiler, and call-graph visualisation. It is genuinely useful when you are working inside a large multi-unit Ada project, because its understanding of the project is derived from the compiler itself rather than from a language server guessing.

![GNAT Studio splash screen — AdaCore's IDE for Ada and SPARK](/img/screenshots/gnatstudio-splash.jpg "GNAT Studio IDE for Ada and SPARK development")

Installation options in 2026 are friendlier than the old installer era: the repository carries **AppImage and Flatpak manifests under `distrib/`**, so a Linux workstation gets a working IDE without touching a package manager. Opening a project is a single flag:

```bash
gnatstudio -P fuel_monitor.gpr
```

Be honest with yourself about the trade-off, though. GNAT Studio is heavy, and many 2026 teams never install it. The **Ada Language Server** — 304 stars and actively developed — speaks the Language Server Protocol, so VS Code, Neovim, Emacs, and Zed all get completion, go-to-definition, inline diagnostics, and GNAT-based refactorings. If your team already lives in one editor, adding a second heavyweight IDE for Ada is friction you can skip. Use GNAT Studio when you want its debugger and call graphs; use the language server when you want Ada to behave like every other language in your editor.

## gnatprove and SPARK: Proving Instead of Testing

This is the part that has no real equivalent in mainstream toolchains. SPARK is a subset of Ada designed for formal analysis, and `gnatprove` is the tool that takes your code plus its contracts and either proves the absence of runtime errors, unproved checks, and violated assertions — or hands you a counterexample.

SPARK analysis is opt-in per unit, which is why adoption is gradual:

```ada
--  src/fuel.ads
package Fuel with SPARK_Mode is

   subtype Percent is Integer range 0 .. 100;

   function Remaining (Total, Used : Percent) return Percent
   with Pre  => Used <= Total,
        Post => Remaining'Result = Total - Used;

end Fuel;
```

```ada
--  src/fuel.adb
package body Fuel with SPARK_Mode is

   function Remaining (Total, Used : Percent) return Percent is
   begin
      return Total - Used;
   end Remaining;

end Fuel;
```

Now the prover has something to work with. The `Pre` contract is a promise your callers must honour; the `Post` contract is a property the prover will verify from the implementation. Run the analysis at level 1, which proves the standard "will not raise a runtime error" suite:

```bash
gnatprove -P fuel_monitor.gpr --level=1 --report=all
```

Levels scale by ambition: **level 0** does flow analysis (uninitialised reads, dead code), **level 1** proves runtime-error freedom, **level 2** adds proof of your user-written assertions, and **level 3–4** push into full functional-correctness territory where the effort curve gets steep. The practical rule from teams who ship this: use level 1 on everything, level 2 where contracts are cheap, and higher levels only on the small number of units that justify the engineering cost.

What makes this different from a linter is the counterexample. When gnatprove cannot prove a check, it reports whether the check is *unproved* (possibly a real bug) or *out of scope* (e.g. floating-point arithmetic it cannot model). You get a concrete input path, not a vague warning. And because the contracts live in the source, they become the specification that survives refactors — a test suite can silently stop testing the important property; a `Post` contract cannot.

Start with `alr with gnatprove` on one unit. You do not need to convert an entire codebase to see value; a single proven buffer-bound function in a parser is worth more than a thousand fuzz cases you cannot reproduce.

## Putting It Together: A Working Project Skeleton

```
fuel_monitor/
├── alire.toml          # pinned toolchain + dependencies
├── fuel_monitor.gpr    # build description, read by gprbuild and Studio
├── src/
│   └── fuel_monitor.adb
└── tests/              # gnattest-generated harnesses land here
```

```ada
--  fuel_monitor.gpr
project Fuel_Monitor is
   for Source_Dirs use ("src");
   for Object_Dir use "obj";
   for Exec_Dir   use "bin";
   for Main       use ("fuel_monitor.adb");
end Fuel_Monitor;
```

Then the whole loop — build, test harness generation, coverage, proof — is three commands:

```bash
alr build
alr exec -- gnattest -P fuel_monitor.gpr     # generate unit-test skeletons
alr exec -- gnatprove -P fuel_monitor.gpr --level=1 --report=all
```

Drop those three lines into CI and you have a pipeline that refuses to merge code the prover cannot discharge. That is the practical difference between "we ran the tests" and "we know the bounds hold."

## Pitfalls When Adopting the Ada Toolchain

- **Version drift between `alr` and your system GNAT.** If you install a distro GNAT *and* an Alire toolchain, you can end up with two compilers on `PATH`. Let Alire own the toolchain; keep distro packages out of the picture.
- **Forgetting `SPARK_Mode` on the body.** A `with SPARK_Mode` on the spec is enough for most units, but mixed setups where the body is excluded will silently reduce what gnatprove can prove. Check the summary table it prints.
- **Chasing level 4 too early.** Full functional proof on floating-point-heavy code is where projects stall. Prove runtime-error freedom first, then add contracts where they pay for themselves.
- **Treating "unproved" as "broken".** Unproved checks are a to-do list, not a verdict. Read the counterexample and decide whether the check needs a stronger precondition, a rework, or a justified exemption.
- **Installing GNAT Studio when the language server would do.** Hundreds of megabytes of IDE to get completion is a bad trade for a VS Code team.
- **Assuming Alire's index covers everything.** It is curated. For a niche library you may need an `externals` declaration pointing at a git URL — that is a feature, not a failure, but budget for it.
- **Skipping the pinned `alire.toml` in source control.** Pinning is the main reason the toolchain is reproducible. Commit it.

## Why Keep the Ada Toolchain Running on Your Own Machines?

Three reasons this stays a local, self-hosted workflow rather than a cloud service. First, **proof runs are CPU-bound and long** — level 2+ on a mid-sized codebase can chew through cores for hours, which is exactly the workload that becomes expensive on metered build infrastructure but free on a workstation you already own. Second, **safety-critical code often cannot leave the building**; if your contracts describe a medical device or a cryptographic core, shipping the source to a hosted prover is a compliance conversation you do not want. Third, **reproducibility**: an `alire.toml` plus a pinned community index snapshot is a complete, auditable description of your build, and it belongs in your repository next to the code.

If you are comparing compiled-language toolchains more broadly, our [Zig vs Rust vs Go systems programming breakdown](../2026-09-02-zig-vs-rust-vs-go-systems-programming-guide/) covers where each ecosystem puts its safety guarantees, and the [Scheme implementations comparison](../2026-09-13-scheme-implementations-racket-chez-guile-comparison/) is a useful contrast for how small-language communities organise compilers and package managers. When you want a browser-based scratchpad for trying generated code and compiler diagnostics, our [self-hosted Compiler Explorer guide](../2026-06-18-self-hosted-compiler-explorer-godbolt-code-analysis/) covers running Godbolt locally.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Ada and SPARK in 2026: Alire vs GNAT Studio vs gnatprove Compared",
  "description": "A practical 2026 comparison of the open-source Ada and SPARK toolchain: Alire as package manager, GNAT Studio and the Ada Language Server as editors, and gnatprove for formal proof of runtime-error freedom.",
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

**Is Ada still worth learning in 2026?**
Yes, for a specific reason: it is the only mainstream-ish language with an open-source toolchain that can formally prove runtime-error freedom. If you work on avionics, rail signalling, medical devices, cryptography, or embedded firmware, that capability is not available in Rust, C++, or Go today. For web CRUD work, Ada is the wrong tool and the ecosystem knows it.

**Do I need GNAT Studio to use Alire or SPARK?**
No. Alire is a command-line tool and gnatprove is a command-line prover. GNAT Studio is optional. Teams using VS Code or Neovim typically install Alire plus the Ada Language Server and never open GNAT Studio at all.

**How does gnatprove differ from a static analyser or linter?**
A linter flags patterns it recognises as risky. gnatprove reasons about every path through your code, using contracts you write, and reports either a proof or a counterexample. It does not heuristically guess; it either discharges the check or shows you an input that breaks it.

**How long does it take to get value from SPARK?**
One unit. Add `SPARK_Mode` to a single package, write one `Pre`/`Post` pair, and run level 1. Teams typically find their first real bug — usually an unhandled edge case in a bounds computation — within the first afternoon.

**Is SPARK a different language I have to learn from scratch?**
No. SPARK is a subset of Ada plus contract annotations. Most ordinary Ada code is already inside the SPARK subset. You exclude the features the prover cannot handle (access types with aliasing in some patterns, tasking) per unit rather than learning a new syntax.

**Can I run this offline in an air-gapped environment?**
Yes, and that is one of the strongest arguments for it. Download the Alire binary and index snapshot, vendor your dependencies, and the whole build-and-prove loop runs with no network access. Nothing about Ada or SPARK requires a vendor service or an internet connection.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
