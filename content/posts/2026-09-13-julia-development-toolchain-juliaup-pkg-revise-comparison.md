---
title: "Julia Toolchain in 2026: Juliaup vs Pkg.jl vs Revise.jl — Stop Restarting Your REPL"
date: "2026-09-13"
description: "How to assemble a reproducible Julia development environment in 2026 with Juliaup, Pkg.jl and Revise.jl: real install commands, Project.toml and Manifest.toml workflows, Docker setups and the traps that break CI."
tags: ["julia", "developer-tools", "package-management", "scientific-computing", "repl"]
cover: "/img/screenshots/julia-language-logo.jpg"
draft: false
---

Julia's dirty secret is not performance — it is that most people evaluate the language with the worst possible toolchain. They install one version system-wide from a distribution package, edit code in one window, and then restart a REPL that takes forty seconds to re-load their packages. Every iteration costs a minute, so they conclude Julia is slow to work in.

**It is not the language. It is the missing toolchain.** Three tools fix it, and each solves a different problem: **Juliaup** manages language versions, **Pkg.jl** manages dependencies reproducibly, and **Revise.jl** reloads your code without restarting the session.

Get all three right and the iteration loop collapses to milliseconds. This guide uses live repository data pulled **2026-09-13** and commands taken from the official documentation.

## TL;DR: The Quick Verdict

- **Juliaup is mandatory and takes one command.** It is the only supported way to install Julia, switch between release and LTS channels, and update without breaking a project.
- **Pkg.jl is not optional either — but use it properly.** Commit `Project.toml` *and* `Manifest.toml`, and run `Pkg.instantiate()` in CI. Half of the "it works on my machine" reports in the Julia ecosystem are one of those two files being missing.
- **Revise.jl is the highest-value five minutes in Julia.** Put three lines in `startup.jl` and you stop restarting your REPL forever.
- **Skip global package installs entirely.** A project-local environment per project costs nothing and removes version conflicts permanently.

## The Three Tools and What They Actually Solve

| Tool | Role | Stars | Last commit | License | Solves |
|---|---|---|---|---|---|
| **Juliaup** | Installer and version manager | 1,302 | 2026-09-11 | MIT | Installing Julia, switching channels, updating safely |
| **Pkg.jl** | Dependency manager (built into Julia) | 670 | 2026-09-13 | MIT | Reproducible builds, project isolation |
| **Revise.jl** | Hot reloading in a live session | 1,355 | 2026-09-02 | MIT | Restarting the REPL, re-loading packages, waiting for compilation |
| **julia** (language) | The runtime itself | 49,094 | 2026-09-13 | MIT | — |

Read those star counts carefully, because they tell a story. **Revise.jl — a package that only makes the REPL nicer — has more stars than Pkg.jl, the package manager.** That is a community telling you which tool changed their daily life.

## Decision Matrix: What to Set Up, in Order

| Your situation | Do this | Why |
|---|---|---|
| Brand-new machine | **Juliaup**, then `juliaup add lts` | One command, clean upgrades, no distro-package archaeology |
| Existing project someone else wrote | `julia --project=. -e 'using Pkg; Pkg.instantiate()'` | Reproduces the exact dependency set from `Manifest.toml` |
| Long interactive session with heavy packages | **Revise.jl** in `startup.jl` | Removes the restart tax entirely |
| CI pipeline | `Pkg.instantiate()` + `Pkg.test()`, never global installs | Deterministic builds; no network surprises mid-run |
| Two projects needing different versions of one package | One environment per project | Isolated `Manifest.toml` per project ends the conflict |
| Building a package other people will use | `Pkg.generate` + `[compat]` bounds | Declares Julia version compatibility explicitly |
| Reproducible container builds | `julia` official image + `JULIA_DEPOT_PATH` pinning | Caches precompilation and pins the depot location |

## Juliaup — Install Julia Correctly, Once

Distribution packages are the most common cause of a stale Julia. Juliaup exists because the language ships frequently and projects need to match versions, so the official recommendation is to install through it rather than through `apt`.

```bash
curl -fsSL https://install.julialang.org | sh
```

The installer is scriptable for provisioning and containers. These arguments come straight from the Juliaup documentation:

```bash
curl -fsSL https://install.julialang.org | sh -s -- \
  --yes \
  --default-channel release \
  --add-to-path=yes \
  --background-selfupdate=0
```

Day-to-day operation is a handful of subcommands:

```bash
juliaup status                 # installed channels and the current default
juliaup list                   # every channel available to install
juliaup add lts                # add the long-term-support channel
juliaup default lts            # make it the default
juliaup update                 # update every installed channel
juliaup update release         # update only the release channel
```

You can also select a channel for one command without changing the default, which is what CI should do:

```bash
julia +lts --version
julia +release --version
```

**Why this matters more than it sounds:** Julia code, package manifests and precompilation caches are tied to specific minor versions. A system package manager that silently upgrades Julia from 1.11 to 1.12 underneath you can invalidate every precompiled cache and, occasionally, a dependency's assumptions. Juliaup makes the version an explicit, inspectable choice.

![The global Julia development and research community](/img/screenshots/julia-language-ecosystem.jpg "The Julia community map published on julialang.org")

## Pkg.jl — Environments, Manifests, and Why You Commit Both Files

Pkg.jl ships with Julia, so there is nothing to install. There are two things to learn instead: **environments** and the difference between `Project.toml` and `Manifest.toml`.

- **`Project.toml`** declares what you depend on: names, UUIDs, version bounds, and your package's own compat requirements. This is the human-authored, commit-it-and-review-it file.
- **`Manifest.toml`** records what was actually resolved: exact versions, git revisions, and the full transitive graph. This is the machine-authored lock file.

**Commit both.** A `Project.toml` alone resolves to whatever is newest today, which is why a build that worked in March fails in September. The `Manifest.toml` is the reproducibility guarantee.

Activate a project-local environment:

```bash
julia --project=.
```

Inside the REPL, the `]` key enters Pkg mode; the equivalent long-form API is:

```julia
using Pkg

Pkg.activate(".")
Pkg.add("DataFrames")            # adds to [deps] and writes both files
Pkg.instantiate()                # reproduce the environment from Manifest.toml
Pkg.status()                     # show direct dependencies
Pkg.resolve()                    # re-resolve after manually editing Project.toml
Pkg.develop(path = "./MyLocalPkg")   # use a local checkout instead of a registry version
Pkg.test()                       # run the package's own test suite
```

A `Project.toml` looks like this — note that `Pkg.add` fills `[deps]` for you, so you should almost never hand-write a UUID:

```toml
name = "HeatSolver"
uuid = "<generated-by-Pkg.generate>"
authors = ["Your Name <you@example.com>"]
version = "0.1.0"

[deps]
# populated automatically by `Pkg.add("...")`

[compat]
julia = "1"

[extras]
Test = "8dfed614-e22c-5e08-85e1-65c5234f0b40"

[targets]
test = ["Test"]
```

In CI, the sequence is always the same three lines — and the reason `instantiate` comes first is that it downloads exactly the versions the manifest pins:

```bash
julia --project=. -e 'using Pkg; Pkg.instantiate()'
julia --project=. -e 'using Pkg; Pkg.test()'
julia --project=. -e 'using Pkg; Pkg.status()'
```

One more habit worth adopting: **never `Pkg.add` into the default environment.** If `julia` starts without `--project`, you are adding to a shared global environment, and six months later you will not know which project needed which package. Keep the default environment empty and it stays a useful signal.

## Revise.jl — the Five Minutes That Removes the Restart Tax

Revise watches your source files and updates method definitions in a running session, so edited code takes effect on the next command instead of after a restart and a re-load. For anyone developing a package, this is the difference between a one-minute loop and a one-second loop.

```julia
import Pkg
Pkg.add("Revise")
```

Then make it load automatically in every session by adding this to `~/.julia/config/startup.jl`, which is the configuration documented by the project:

```julia
try
    using Revise
catch e
    @warn "Error initializing Revise" exception = (e, catch_backtrace())
end
```

The `try`/`catch` is not paranoia — a broken Revise should warn and let your session continue rather than prevent Julia from starting at all.

Typical uses:

```julia
# after editing src/HeatSolver.jl in your editor:
julia> using HeatSolver
julia> HeatSolver.solve(grid)      # picks up the version on disk right now

# switch git branches and keep working — no restart
```

Revise also handles changes to package code you are developing with `Pkg.develop`, which is exactly the workflow where people feel the restart cost most.

**Two limits worth knowing.** Revise cannot track changes that alter a type's layout or a struct definition in ways requiring recompilation of dependent code — you will still restart occasionally. And mixing Revise with Pkg-mode package edits in the same session is a known source of confusion: if behaviour looks impossible, restart once and check whether the problem was Revise's stale view of a struct.

## A Container Setup That Reproduces in CI

Combining all three tools in a container gives you a development environment that CI can rebuild byte for byte:

```yaml
services:
  julia:
    image: julia:latest          # pin an exact tag in production
    container_name: julia-dev
    working_dir: /work
    environment:
      - JULIA_DEPOT_PATH=/work/.julia
      - JULIA_NUM_THREADS=4
    volumes:
      - ./app:/work
    command: >
      bash -lc "julia --project=/work -e 'using Pkg; Pkg.instantiate()' &&
      julia --project=/work"
    stdin_open: true
    tty: true
```

```bash
docker compose up -d
docker compose exec julia julia --project=/work -e 'using Pkg; Pkg.status()'
docker compose exec julia julia --project=/work -e 'using Pkg; Pkg.test()'
```

`JULIA_DEPOT_PATH` is the part people leave out. It controls where packages, compiled caches and registries live, and pointing it inside the mounted working directory means your precompilation cache survives container restarts — which turns a multi-minute cold start into seconds. In CI, mounting or caching that directory is usually the single biggest build-time win available.

## Pitfalls That Break Julia Projects in Practice

- **Committing `Project.toml` without `Manifest.toml`.** Without the manifest, `Pkg.instantiate()` resolves to the newest compatible versions, so the same commit builds differently in two months. For applications, always commit both.
- **Installing packages into the default environment.** `Pkg.add` without `--project` writes to the shared environment. Use `--project=.` everywhere, including in Makefiles and CI scripts.
- **Editing `Project.toml` by hand and forgetting `Pkg.resolve()`.** Pkg reads the manifest, not your edit. Add the dependency through `Pkg.add` or run `Pkg.resolve()` immediately afterwards.
- **Expecting a copied depot to be portable.** Precompilation caches embed paths and can be invalidated when absolute paths change. Cache the depot inside the same path you use at runtime.
- **`Pkg.develop` paths escaping the build context.** A local path dependency that exists on your laptop but not in CI produces a manifest that cannot be instantiated. Keep local `dev` dependencies out of committed manifests for released code.
- **Ignoring the precompilation tax.** The first `using` after an update recompiles dependencies. That is expected, not a bug — and it is why the depot cache matters.
- **Threads default to one.** `JULIA_NUM_THREADS` must be set before Julia starts; `Threads.nthreads()` will otherwise report 1 no matter how many cores the machine has.

## Why a Reproducible Scientific Stack Is Worth the Setup

Julia's audience is scientific computing, and scientific computing has a reproducibility problem that has nothing to do with code quality. A result you cannot rebuild is not a result — and in Julia, the two files that make rebuilding possible are `Project.toml` and `Manifest.toml`.

Self-hosting this stack has three concrete payoffs. First, **version pinning across the whole graph**: the language channel, the dependency versions and the compiled caches are all declared, so a reviewer gets your numbers, not an approximation. Second, **no dependency on a hosted build service**: long simulations cannot be pushed through an external CI runner on a per-commit basis, so the toolchain has to live where the data lives. Third, **cost control**: simulation jobs are long and predictable, which is the one workload shape where owning the hardware beats renting it.

If Julia is where you do your numerical work, two related guides are worth reading alongside this one: our comparison of [Julia web frameworks](../2026-09-04-julia-web-frameworks-genie-oxygen-httpjl-comparison/) covers what to build around a Julia service, and the [Julia plotting library comparison](../2026-09-05-julia-plotting-libraries-makie-plots-gadfly-comparison/) covers the output side. If your workflow is notebook-first rather than REPL-first, the [self-hosted reactive notebook guide](../2026-06-09-self-hosted-reactive-notebooks-marimo-livebook-jupyterlite-guide/) covers Marimo, Livebook and JupyterLite — which is a different answer to the same iteration-speed problem.

The recurring theme across all three is the same: **the environment is part of the experiment.** Declare it in files, pin it in a container, and the argument about results becomes about the results.

## FAQ

**What is Juliaup and do I need it?**

Juliaup is the official installer and version manager for Julia. You need it if you care about reproducing builds, because it lets you install several Julia versions side by side, switch the default channel, and update deliberately rather than as a side effect of a system upgrade. It installs with a single command and replaces distribution packages.

**What is the difference between Project.toml and Manifest.toml?**

`Project.toml` is what you declare — dependency names, UUIDs and version bounds. `Manifest.toml` is what Pkg.jl resolved — the exact versions and git revisions of your whole dependency graph. Commit both for anything that must build reproducibly; the manifest is the lock file that makes `Pkg.instantiate()` deterministic.

**Do I need Revise.jl, or is restarting the REPL fine?**

Restarting is fine until you are developing a package, at which point the restart-plus-reload cycle dominates your working time. Revise.jl updates method definitions in a live session so edits take effect immediately. It costs one dependency and three lines in `startup.jl`, making it the best effort-to-benefit ratio in the Julia ecosystem.

**How do I make Julia builds reproducible in CI?**

Pin the Julia version explicitly (Juliaup channel or a pinned container tag), set `JULIA_DEPOT_PATH` so the package depot and precompilation cache are cacheable, and run `julia --project=. -e 'using Pkg; Pkg.instantiate()'` before tests. Never install packages globally in CI — reproduce the environment from the manifest instead.

**Why does Julia recompile packages every time I update something?**

Julia compiles specialised code for your types on demand and caches the result in the depot, keyed by package version and environment. Updating a dependency invalidates the affected caches, so the next `using` rebuilds them. Keeping `JULIA_DEPOT_PATH` in a persistent location turns that cost into a one-time expense per version, rather than a per-container-restart one.

**Can I keep multiple Julia versions installed at once?**

Yes — that is precisely what Juliaup is for. `juliaup add lts` installs the long-term-support channel alongside your default, `julia +lts` runs a single command against it, and `juliaup default lts` changes the default. Projects that pin their channel in documentation or CI stay consistent regardless of what the machine's default happens to be.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Julia Toolchain in 2026: Juliaup vs Pkg.jl vs Revise.jl — Stop Restarting Your REPL",
  "description": "How to assemble a reproducible Julia development environment in 2026 with Juliaup, Pkg.jl and Revise.jl, including Project.toml and Manifest.toml workflows, Docker setups and CI pitfalls.",
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
