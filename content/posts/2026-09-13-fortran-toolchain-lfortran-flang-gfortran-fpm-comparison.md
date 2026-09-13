---
title: "Fortran in 2026: LFortran vs Flang vs gfortran — Which Compiler Should You Actually Use?"
date: "2026-09-13"
description: "A hands-on 2026 comparison of the three production Fortran compilers — LFortran, LLVM Flang and gfortran — plus fpm and fortls, with real install commands, Docker configs and migration traps."
tags: ["fortran", "compilers", "hpc", "developer-tools", "scientific-computing"]
cover: "/img/screenshots/lfortran-toolchain-cover.jpg"
draft: false
---

Fortran is 69 years old, and it is still the language that produces the weather forecast you read this morning, the finite-element stress numbers behind every bridge inspection, and a large share of the world's climate simulation output. The language never lost its job. What did change — quietly, over the last three years — is the toolchain around it. In 2026 you no longer have exactly one realistic compiler choice, and that is genuinely new.

**The practical question is no longer "Is Fortran dead?" It is "which Fortran compiler and build stack do I put in my container image?"** And the answer depends entirely on whether you are shipping a 400,000-line production model to a national supercomputer, or prototyping a numerical method on a laptop at 1 a.m.

This guide answers that with live repository data (pulled **2026-09-13**), real install commands taken from the official repositories, and a working Docker setup you can paste into a project today.

## TL;DR: The Quick Verdict

- **Production HPC code that must compile today: `gfortran` + `fpm`.** gfortran has the most complete standard coverage, the widest MPI/OpenMP ecosystem, and every Linux distribution ships it. fpm removes the Makefile archaeology.
- **Interactive exploration, teaching, and notebook work: LFortran.** It is the only Fortran compiler with a real REPL and a Jupyter kernel, and it compiles and runs a growing subset of the language instantly.
- **Vendor toolchains, GPU offload, and MLIR-based pipelines: Flang.** It lives inside LLVM, so it inherits the entire LLVM optimizer and offload story.
- **Install `fortls` regardless of which one you pick.** One `pip install` turns any editor into a Fortran IDE. Skipping this is the single most common self-inflicted wound in Fortran development.

## The 2026 Fortran Toolchain Compared

| Tool | Role | License | Stars | Last commit | Standout strength |
|---|---|---|---|---|---|
| **LFortran** | Compiler, REPL, notebook kernel | Open source (repo license) | 1,240 | 2026-09-13 | Instant compilation, interactive REPL, Jupyter kernel |
| **Flang** | LLVM Fortran frontend | Apache-2.0 (LLVM exception) | part of `llvm/llvm-project` (40,441) | 2026-09-13 | MLIR-based optimization, GPU offload, vendor adoption |
| **gfortran** | GNU Fortran compiler | GPL-3.0 with runtime exception | ships with GCC | tracks GCC releases | Most complete standard coverage, universal availability |
| **fpm** | Fortran Package Manager | MIT | 1,071 | 2026-09-03 | Manifest-driven builds, dependency resolution |
| **fortls** | Language server | MIT | 339 | 2026-08-31 | Autocomplete, go-to-definition, hover signatures |

Two things about that table deserve emphasis. First, **LFortran is committing daily** — that is not a hobby project coasting on curiosity; it is an active compiler implementation with a published progress page tracking language coverage. Second, **`fortls` at 339 stars vastly understates its importance** — it is the piece that makes the other four usable inside an editor.

## Decision Matrix: Pick in Ten Seconds

| Your situation | Pick | Why |
|---|---|---|
| Legacy production model, MPI + OpenMP, must build tonight | **gfortran** | Complete standard support, mature OpenMP, distro packages, every HPC center has it |
| New greenfield numerical project | **fpm + gfortran** | Real dependency management, no Makefile, `fpm test` built in |
| Teaching Fortran, or a REPL-driven numerical experiment | **LFortran** | The only interactive Fortran; errors are instant, not a link step later |
| Targeting GPUs through LLVM offload | **Flang** | Shares the LLVM offload and target stack with clang |
| You maintain a CI pipeline across compilers | **All three + fpm** | Catching compiler-specific behaviour early is worth the extra stage |
| You write Fortran in VS Code or Neovim | **fortls** | Works with any of the above; no lock-in |

## LFortran — the Interactive Compiler

LFortran is the answer to a question Fortran developers stopped asking decades ago: *what if a compiler were fast enough to feel like a scripting language?* Its pitch is a compiler built around a modern intermediate representation rather than a pile of legacy passes, plus three things no Fortran toolchain had before: a REPL, a notebook kernel, and compile times measured in milliseconds for the interactive subset.

Install it through conda-forge, which is the officially recommended route:

```bash
conda create -n lf
conda activate lf
conda install lfortran -c conda-forge

which lfortran          # confirm $CONDA_PREFIX/bin/lfortran
lfortran --version
```

The interactive prompt is where it earns its keep:

```bash
lfortran
```

```text
>>> integer :: n = 10
>>> real :: x
>>> x = sqrt(real(n)) * 3.14159
>>> print *, x
```

Add Jupyter and you get a Fortran notebook — which, if you have ever tried to teach numerical methods to undergraduates, is a genuinely different experience:

```bash
conda install jupyter -c conda-forge
jupyter notebook
# New -> Fortran
```

![LFortran compiler progress toward full language coverage](/img/screenshots/lfortran-toolchain-cover.jpg "LFortran's published progress toward complete language coverage, hosted at lfortran.org")

**Where it will bite you:** LFortran does not yet compile the entire language, and it will tell you so honestly rather than silently miscompiling. Before you move a production solver onto it, read the project's own progress page and test your actual code. Treat LFortran as the fast lane for iteration and a promising production compiler — not as a drop-in replacement for a codebase relying on every corner of Fortran 2018.

## Flang — LLVM's Fortran Frontend

Flang is the Fortran frontend inside `llvm/llvm-project`, built on the FIR dialect in MLIR. Its strategic value is integration: same optimizer as clang, same target backends, same offload machinery, same release cadence. If your organization already builds an LLVM-based toolchain for another language, Flang slots into it.

Install from the LLVM apt repository:

```bash
wget https://apt.llvm.org/llvm.sh
chmod +x llvm.sh
sudo ./llvm.sh 20
sudo apt-get install -y flang-20
```

**Naming trap:** the driver binary was historically `flang-new`. Recent LLVM releases promote it to `flang`. Always check what your installed package provides instead of assuming:

```bash
command -v flang flang-new || ls /usr/lib/llvm-20/bin | grep -i flang
```

Build a real program with OpenMP offload targets in mind:

```bash
flang -O3 -fopenmp -fopenmp-targets=nvptx64-nvidia-cuda -o solver solver.f90
```

Flang's weakness has nothing to do with technical quality — it is ecosystem age. Some legacy codes depend on gfortran-specific extensions, and vendor Fortran libraries are usually tested against gfortran first. Flang is the right choice for new LLVM-centric work and the wrong choice if you need a decade-old code to build with zero edits this afternoon.

## gfortran — the Default That Just Works

gfortran is what `apt install` gives you, what most of the world's Fortran is compiled with, and — for the overwhelming majority of users — what you should use. It is part of GCC, so it follows GCC's release train and benefits from the same optimization work.

```bash
sudo apt-get install -y gfortran
gfortran --version
gfortran -O2 -march=native -fopenmp -o solver solver.f90
./solver
```

For development builds, turn on the checks that catch real bugs in numerical code:

```bash
gfortran -O0 -g -Wall -Wextra -fimplicit-none -fcheck=all -ffpe-trap=invalid,zero,overflow \
  -o solver-debug solver.f90
```

`-fimplicit-none` alone will find bugs in older code that a reviewer never will, because implicit typing turns a typo into a new variable that silently holds zero. Add `-fcoarray=single` or `-fcoarray=lib` if your code uses coarrays.

The trade-off is honest: gfortran is not the fastest-moving compiler, and its error messages remain terse. But **when a 30-year-old model must build on a machine you do not control, gfortran is the choice that gets you home.**

## fpm — the Package Manager That Ends Makefile Archaeology

fpm (Fortran Package Manager, **v0.13.0**, MIT) is the least glamorous and most transformative tool in this list. It gives Fortran what every modern language assumed it already had: a manifest, a dependency resolver, and a test runner.

```bash
conda config --add channels conda-forge
conda create -n fpm fpm
conda activate fpm
fpm --version
```

Homebrew users can use the official tap instead:

```bash
brew tap fortran-lang/fortran
brew install fpm
```

Linux binaries are published on the releases page; the current asset name is `fpm-0.13.0-linux-x86_64-gcc-12`:

```bash
curl -fsSL -o /usr/local/bin/fpm \
  https://github.com/fortran-lang/fpm/releases/download/v0.13.0/fpm-0.13.0-linux-x86_64-gcc-12
chmod +x /usr/local/bin/fpm
```

A project is one command:

```bash
fpm new heat-solver
cd heat-solver
fpm build
fpm test
fpm run
```

That creates the layout fpm expects — `src/`, `app/`, `test/`, `example/` — and generates a manifest. Here is a realistic one with a real dependency:

```toml
name = "heat-solver"
version = "0.1.0"
license = "MIT"
author = "Your Name"
maintainer = "you@example.com"

[build]
auto-executables = true
auto-tests = true
auto-examples = true

[library]
source-dir = "src"

[install]
library = true

[dependencies]
stdlib = { git = "https://github.com/fortran-lang/stdlib", tag = "v0.7.0" }
```

Then `fpm build` resolves, fetches, and builds the dependency tree — no vendored copies, no hand-maintained include order. **If you adopt one thing from this article and nothing else, adopt fpm.** It is MIT-licensed, it does not lock you into a compiler, and it converts a build system that lived in one person's head into a file in version control.

## fortls — the Language Server Nobody Installs Until They Try It

fortls is a Fortran language server that speaks the standard Language Server Protocol, so it works in VS Code, Neovim, Emacs, Sublime, and anything else with an LSP client. It gives you autocomplete for your own modules, go-to-definition across a project, hover signatures for intrinsics, and inline diagnostics.

```bash
pip install fortls
```

If you previously installed the older `fortran-language-server`, remove it first — both claim the same binary name and the conflict produces maddening editor behaviour:

```bash
pip uninstall fortran-language-server
pip install fortls --upgrade
```

Configure it with a `.fortls` file at your project root:

```json
{
  "fortran_dialect": "f2008",
  "hover_signature": true,
  "use_signature_help": true,
  "incl_suffixes": [".f90", ".F90", ".f95", ".f03", ".f08"]
}
```

**This is the highest return-per-keystroke change you can make to a Fortran workflow**, and it is compiler-agnostic — the same setup serves gfortran, Flang and LFortran projects.

## Running the Whole Toolchain in One Container

The reliable way to make all of the above reproducible is a container, because conda-forge carries `lfortran`, `fpm`, `fortls` and `gfortran` in one place. This compose file gives you a complete Fortran development environment, including notebooks:

```yaml
services:
  fortran:
    image: condaforge/miniforge3:latest
    container_name: fortran-dev
    working_dir: /work
    volumes:
      - ./src:/work
      - conda-pkgs:/opt/conda/pkgs
    environment:
      - CONDA_ENV=fortran
    command: >
      bash -lc "conda create -y -n fortran -c conda-forge
      lfortran fpm fortls gfortran cmake ninja jupyterlab &&
      conda run -n fortran jupyter lab --ip=0.0.0.0 --no-browser --allow-root"
    ports:
      - "8888:8888"
    restart: unless-stopped

volumes:
  conda-pkgs:
```

Bring it up, then use the environment for both compilers:

```bash
docker compose up -d
docker compose exec fortran bash -lc "conda run -n fortran gfortran --version"
docker compose exec fortran bash -lc "conda run -n fortran lfortran --version"
docker compose exec fortran bash -lc "conda run -n fortran fpm test"
```

Because the environment is declared in a file, "it compiles on my machine" stops being a conversation. **This matters more in Fortran than in most ecosystems**, because numerical results depend on compiler version, optimization level and fast-math flags — differences that are invisible until a reviewer cannot reproduce your figures.

## Common Pitfalls When Mixing Fortran Toolchains

- **`.mod` files are compiler- and version-specific.** A `module` compiled by gfortran cannot be consumed by Flang or LFortran, even from identical source. Never mix object files from two compilers in one link — you will get link errors in the best case and wrong results in the worst.
- **Runtime libraries do not travel.** Linking a gfortran-built static library into a Flang program drags in `libgfortran` and mixes I/O implementations. Build the entire dependency tree with one compiler.
- **`flang-new` vs `flang`.** The driver was renamed across LLVM releases. Scripts that hardcode `flang-new` break silently on newer packages.
- **Implicit typing hides typos.** `-fimplicit-none` plus `-fcheck=all` during development catches uninitialized variables and out-of-bounds access that optimization-level bugs disguise.
- **fpm's directory conventions are not optional.** Sources outside `src/` are not part of the library unless declared. If `fpm build` ignores a file, the manifest is usually the reason.
- **MPI wrappers must match the compiler used for the MPI build.** `mpif90` from an OpenMPI stack built against one compiler will not accept objects produced by another. Check `mpif90 --showme:command`.
- **Conda and system compilers fight over `PATH`.** If `which gfortran` points into a conda environment but your MPI came from the distribution, you are mixing toolchains without meaning to.

## Why Self-Host a Reproducible Fortran Toolchain?

Fortran's centre of gravity is scientific and engineering work, where reproducibility is not a nicety — it is the deliverable. If a reviewer, an auditor or a colleague cannot rebuild your solver and get the same numbers, the toolchain is the problem, not the physics.

Self-hosting gives you control over three things that managed environments take away. First, **compiler version pinning**: your container records the exact gfortran or Flang release, so a distribution upgrade three months from now cannot change your results. Second, **private dependencies**: many numerical libraries are shipped as tarballs with restrictive redistribution terms, and a local fpm registry or artifact store handles that cleanly. Third, **cost and data locality**: simulation inputs are frequently measured in terabytes and cannot be pushed through an external build service.

If you run simulations on a cluster, the toolchain pairs naturally with a proper job scheduler — our comparison of [self-hosted HPC workload managers](../2026-05-02-slurm-vs-openpbs-vs-htcondor-self-hosted-hpc-workload-managers-guide/) covers Slurm, OpenPBS and HTCondor, and the [HPC container runtime guide](../2026-06-01-self-hosted-hpc-container-runtimes-apptainer-charliecloud-podman-hpc-guide/) explains where Apptainer fits alongside the Docker recipe above. For quick experiments without any local setup, a [self-hosted compiler explorer](../2026-06-18-self-hosted-compiler-explorer-godbolt-code-analysis/) lets you diff compiler output across gfortran, Flang and LFortran side by side. And if your simulator is a smaller standalone tool rather than a wall-sized model, our [systems programming language comparison](../2026-09-02-zig-vs-rust-vs-go-systems-programming-guide/) covers the alternatives people reach for when starting fresh.

The pattern is the same in all four cases: put the toolchain in version control, and the argument about results becomes reproducible instead of verbal.

## FAQ

**Is gfortran still the best Fortran compiler in 2026?**

For production work, yes. gfortran has the most complete standard coverage, the widest MPI and OpenMP support, and it is available in every Linux distribution. Flang is technically excellent and better integrated with LLVM tooling, but the surrounding ecosystem still assumes gfortran. If your code must build today on hardware you do not control, gfortran remains the lowest-risk choice.

**Should I switch from gfortran to LFortran?**

Not for an existing production codebase — yet. Switch the *iteration loop*: use LFortran's REPL and notebook kernel to develop algorithms quickly, then build and test with gfortran for release. LFortran does not yet compile the complete language, so treat it as a fast development lane rather than a drop-in replacement.

**What is fpm, and do I need it?**

fpm is the Fortran Package Manager: manifests in `fpm.toml`, automatic dependency resolution, and built-in test and example runners. You do not strictly need it — plenty of working codes use hand-written Makefiles. But if your build instructions depend on one specific person's memory, fpm converts that into a reviewed file. It is MIT-licensed and works with gfortran, Flang or LFortran.

**Can I mix gfortran and Flang object files in one program?**

No. Fortran compiler module files (`.mod`) and runtime libraries are not interchangeable between compilers. Mixing them typically produces link errors mentioning unresolved symbols; when it does link, behaviour around I/O and floating-point handling can differ subtly. Compile the full dependency tree with a single compiler.

**Do I need a language server for Fortran in 2026?**

Yes. `pip install fortls` plus any LSP-capable editor gives you autocomplete for your own modules, cross-file go-to-definition, hover signatures for intrinsics, and inline diagnostics — in a language where a typo normally becomes a silently zero-valued variable. It works with gfortran, Flang and LFortran projects alike.

**Is Fortran actually worth learning or maintaining in 2026?**

If you care about numerical performance and long-lived code, yes. Numerical weather prediction, computational fluid dynamics, structural analysis and much of computational chemistry still run on Fortran, and modern Fortran (2008 onward) is a genuinely pleasant array language. The toolchain has finally caught up with the language, which is the real news in 2026.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Fortran in 2026: LFortran vs Flang vs gfortran — Which Compiler Should You Actually Use?",
  "description": "Hands-on 2026 comparison of LFortran, LLVM Flang and gfortran, plus fpm and fortls, with real install commands, Docker Compose configs and migration pitfalls.",
  "datePublished": "2026-09-13",
  "dateModified": "2026-09-13",
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
