---
title: "Dune vs Opam vs Esy in 2026: Which OCaml Build Toolchain Should You Actually Use?"
date: "2026-10-24"
tags: ["ocaml", "build-systems", "package-management", "developer-tooling", "functional-programming"]
cover: "/img/screenshots/dune-build-system-logo.jpg"
draft: false
---

OCaml teams lose more hours to build plumbing than to the type system. A fresh clone that takes 40 minutes to compile, a CI job that passes locally and fails on the runner because someone's `opam switch` had a different `dune` binary, or a monorepo where the formatter version silently rewrote 300 files — these are toolchain problems, not language problems. And the OCaml toolchain is unusual among modern ecosystems: **two package managers and one build system coexist, and they are not interchangeable.**

This guide compares the three tools you will actually be asked to choose between in 2026 — **Dune**, **Opam**, and **Esy** — with current repository data, real configuration files pulled from the official projects, and an opinionated answer for each situation.

## TL;DR: The 30-Second Verdict

- **Starting a new OCaml project in 2026?** Use **Dune** for the build and **Opam** for the compiler/dependency layer. That is the path every upstream project, every tutorial, and ocaml.org's own package index assume.
- **Managing multiple compiler versions, or pinning a dependency to a git branch?** That is **Opam**'s job — Dune does not install anything and never will.
- **Shipping an OCaml/Reason component into an npm monorepo, or reusing `package.json` tooling?** Use **Esy**. It is the only one of the three built around the npm mental model.
- **Never** run Esy and Opam against the same project directory. Pick one and document it in the README on day one.

## Comparison Table: The Three Tools Side by Side

| Dimension | **Dune** | **Opam** | **Esy** |
|---|---|---|---|
| Primary role | Composable build system (compile, test, docs, fmt) | Source-based package manager + compiler switch manager | `package.json`-style package manager for native code |
| Latest repo stats | 1,933 ★ · pushed 2026-10-24 | 1,384 ★ · pushed 2026-10-19 | 853 ★ · pushed 2026-09-24 |
| License | MIT | LGPL-2.1 with linking exception | MIT-style (custom) |
| Config file | `dune-project` + per-directory `dune` | `<pkg>.opam` + `~/.opam` switches | `package.json` + `esy.lock/` |
| Installs dependencies | ❌ No | ✅ Yes | ✅ Yes |
| Manages compiler versions | ❌ No | ✅ Yes (`opam switch`) | ⚠️ Indirectly (per-sandbox) |
| Native npm dependency support | ❌ | ❌ | ✅ |
| Monorepo / multi-package | ✅ `(include_subdirs)`, workspace builds | ⚠️ Via pins | ✅ Workspaces |
| Watch mode | ✅ `dune build -w` | ❌ | ✅ `esy build --watch` |
| Official docs compiler | ✅ `odoc` integration built in | ⚠️ Manual | ⚠️ Manual |
| Learning curve | Low-medium | Medium | Medium-high |

Star counts and last-push dates were pulled from the official GitHub repositories at publish time; they move weekly, so treat them as a snapshot, not a constant.

![Dune build system logo](/img/screenshots/dune-build-system-logo.jpg "Dune is the de facto OCaml build system in 2026")

## Decision Matrix: Pick in Ten Seconds

| Your situation | Use this | Why |
|---|---|---|
| New library or CLI, single compiler | **Dune + Opam** | Zero friction, all upstream templates assume it |
| Supporting OCaml 4.14 and 5.3 simultaneously | **Opam** switches (+ Dune) | `opam switch` isolates compilers cleanly |
| Migrating a Reason/ReScript app into an npm monorepo | **Esy** | Consumes `package.json`, plays well with npm scripts |
| Building the same project on macOS, Linux, and in CI | **Dune + Opam lockfile** | Deterministic builds without a second package format |
| Needing a git dependency pinned to a commit | **Opam** (`opam pin`) | First-class pinning with automatic re-resolution |
| Enforcing formatting across 40 contributors | **Dune + ocamlformat** | `dune fmt` is a single command, version pinned in-repo |
| Publishing to opam-repository | **Opam** | The only path to `opam install <your-package>` |

## Dune: The Build System That Won

Dune's pitch is that you describe *what* a directory contains, not *how* to compile it. There are no Makefiles, no per-file rules, and no ordering declarations — module dependency graphs are computed automatically from the code. That is why the repository description is literally "a composable build system for OCaml."

A real `dune-project` from a current upstream project (`ocaml/odoc`, fetched from the repository) looks like this:

```lisp
(lang dune 3.21)

(name odoc)

(documentation "https://ocaml.org/p/odoc")

(source
 (github ocaml/odoc))

(license ISC)
```

The `(lang dune 3.21)` line is a hard contract with the installed binary: a `dune` older than the declared language version refuses to run. That is intentional — it prevents silent semantics drift between contributors — but it is also the single most common source of "works on my machine" failures in OCaml CI. Pin your `dune` version in the CI image, not in someone's shell history.

Per-directory `dune` files then stay tiny:

```lisp
(library
 (name mylib)
 (libraries unix str)
 (preprocess (pps ppx_deriving.show)))

(executable
 (name main)
 (libraries mylib))

(test
 (name test_mylib)
 (libraries mylib alcotest))
```

Day-to-day commands:

```bash
dune build                 # build everything
dune build @install        # build what would be installed
dune runtest               # run all tests, cached
dune utop                 # REPL with your libraries loaded
dune fmt                   # format every file via ocamlformat
dune build -w              # watch mode: rebuild on save
dune build --profile release --root .
```

Two features deserve emphasis because they change team behaviour rather than just compile speed:

1. **Watch mode with incremental compilation.** In a mid-size codebase `dune build -w` keeps a hot compiler process and re-checks only the affected modules. Edits to a leaf module typically re-verify in well under a second, which turns the type checker into an active design tool instead of a batch step.
2. **`dune fmt` + a pinned `.ocamlformat`.** Formatting arguments in OCaml are genuinely endless; resolving them in a committed config file ends the debate. A real `.ocamlformat` from `ocaml/odoc`:

```ini
module-item-spacing=preserve
version=0.27.0
ocaml-version=4.02
```

The `version=` field is mandatory on purpose: it pins the formatter's opinion so that a newer `ocamlformat` cannot reformat the tree behind your back.

## Opam: The Package and Compiler Layer Dune Refuses to Be

Dune compiles; Opam provisions. It is a **source-based** package manager, which is why OCaml dependencies can be patched, pinned, and cross-compiled in ways binary-only registries struggle with. Its description sums up the design: multiple simultaneous compiler installations, flexible package constraints, and a git-friendly workflow.

The core move every OCaml developer needs in muscle memory:

```bash
# Create an isolated switch with a specific compiler
opam switch create myproj 5.3.0
eval $(opam env --switch=myproj --set-switch)

# Install dependencies only (no dev tools), for CI
opam install --deps-only --with-test -y .

# Pin a dependency to a local checkout or a git commit
opam pin add mylib . --kind=path
opam pin add otherlib https://github.com/example/otherlib.git#a1b2c3d

# Export a lockfile-style snapshot for reproducible CI
opam lock .        # produces <pkg>.opam.locked
```

An `.opam` file is the package's public API to the ecosystem, and the fields that matter most in practice are `depends`, `depopts`, and `build`:

```opam
opam-version: "2.0"
synopsis: "Example library"
maintainer: "you@example.com"
license: "MIT"
depends: [
  "ocaml" {>= "4.14"}
  "dune" {>= "3.0"}
  "alcotest" {with-test}
]
build: [
  ["dune" "subst"] {dev}
  ["dune" "build" "-p" name "-j" jobs]
  ["dune" "runtest" "-p" name] {with-test}
]
```

Note how the `build:` field is just a list of `dune` invocations. That is the real division of labour: **Opam owns resolution and installation, Dune owns compilation semantics.** When someone asks "should I switch from Dune to Opam", the honest answer is that the question does not parse.

Where Opam genuinely hurts: switch sprawl. Three projects, four switches, and a `PATH` that depends on which terminal tab you're in is a normal Tuesday. Fix it with per-directory `.envrc` (direnv) or local switches created inside the repo (`opam switch create . --deps-only`), which makes the switch as local as the code.

## Esy: The npm-Shaped Option

Esy exists because OCaml does not live in a vacuum. If your team already runs a JavaScript monorepo, "install another package manager with its own registry" is a hard sell. Esy answers with `package.json`: dependencies are declared in the same file format as npm, resolved from npm *and* opam, and installed into a project-local sandbox instead of a global switch.

```json
{
  "name": "my-native-app",
  "version": "0.1.0",
  "description": "Reason/OCaml component inside an npm workspace",
  "license": "MIT",
  "esy": {
    "build": "dune build -p #{self.name}",
    "buildEnv": { "DUNE_BUILD_DIR": "#{self.target_dir}" }
  },
  "dependencies": {
    "@opam/dune": "*",
    "@opam/lwt": "^5.7.0",
    "@opam/alcotest": "*",
    "ocaml": "~5.1.0"
  },
  "devDependencies": {
    "@opam/ocaml-lsp-server": "*"
  }
}
```

```bash
npm install -g esy
esy install     # resolve and fetch into ./_esy
esy build       # run the configured build command
esy x my-native-app
esy build --watch
```

The tradeoffs are real and worth stating bluntly:

- **Sandbox isolation is Esy's killer feature.** Every project gets its own resolved store; there is no global switch to corrupt, and `rm -rf _esy && esy install` reproduces the environment.
- **The ecosystem is smaller.** esy.sh's package overlay lags opam-repository, and packages that rely on unusual build steps sometimes need an `@opam/` override. Expect to write a small `esy.json` patch for maybe one dependency in five.
- **Documentation assumes Dune + Opam.** Tutorials, blog posts, and most upstream `CONTRIBUTING.md` files will not mention Esy at all, so new contributors pay a discovery tax.

If your project has zero npm surface area, Esy adds a layer without buying you much. If you are shipping a native binary *into* a JS build pipeline, it removes an entire class of integration work.

## Reproducible Builds in CI: What Actually Breaks

The failure mode that costs the most time is not picking the "wrong" tool — it is an unpinned combination of all three. Concretely:

1. **Pin the base image, not just the package list.** Use the official `ocaml/opam` images (e.g. `ocaml/opam:debian-12-ocaml-5.3`) so the compiler and system libraries match between laptop and runner.
2. **Commit the resolved state.** `opam lock` output or `esy.lock/` belongs in git. Floating `{>= "4.14"}` constraints are how a green build turns red on a Sunday.
3. **Cache the right directory.** For Dune, cache `_build` keyed on `dune-project` + lockfile. For Opam, cache `~/.opam` keyed on the switch name. Caching the wrong path gives you the illusion of speed with none of the correctness.
4. **Run the formatter as a check, not a fix, in CI.** `dune build @fmt --auto-promote` locally, `dune build @fmt` in CI. Otherwise CI quietly rewrites files and the diff nobody reviewed gets merged.
5. **Do not mix sandboxes.** An Esy project that shells out to a `dune` installed by Opam will pick up the wrong standard library the moment a version mismatch appears. Use `esy x dune ...` or a pinned `@opam/dune` dependency.

A minimal GitHub Actions job that respects all five:

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    container: ocaml/opam:debian-12-ocaml-5.3
    steps:
      - uses: actions/checkout@v4
      - run: sudo chown -R opam:opam /__w
      - run: opam install --deps-only --with-test -y .
      - run: opam exec -- dune build @install @fmt
      - run: opam exec -- dune runtest
```

That is roughly 90 seconds cold on a small library — and, more importantly, it is the *same* 90 seconds on every machine, which is the entire point.

## Migration Notes and Common Traps

- **`(lang dune X.Y)` is a floor, not a target.** Bumping it to get a new feature silently raises the minimum `dune` for everyone, including CI images you do not control. Bump it in its own commit with a note.
- **`opam switch` does not affect an already-open shell.** If your build suddenly can't find a library, check `opam switch` and `eval $(opam env)` before debugging the code.
- **`ocamlformat` version must be pinned per project.** A global `ocamlformat` binary plus no `version=` field in `.ocamlformat` produces spurious diffs across the whole tree.
- **Esy + Opam in one repo is a trap for contributors.** If you must support both, provide a `Makefile` with explicit `esy` and `opam` targets and say which one is canonical.
- **`dune runtest` caches aggressively.** When a test "doesn't reflect your change", `dune runtest --force` distinguishes a stale cache from a real bug.
- **Vendored dependencies hide version drift.** `(vendored_dirs vendor)` is great for hermetic builds and terrible for security updates unless you track upstream commits deliberately.

For a deeper look at how these pieces fit into an actual application stack, see our comparison of [OCaml web frameworks Dream, Opium and Ocsigen](../2026-09-04-ocaml-web-frameworks-dream-opium-ocsigen-comparison/) and the [OCaml testing libraries shootout](../2026-08-01-ocaml-testing-libraries-ounit-alcotest-qcheck/) — both assume a working Dune setup, which is exactly why getting the toolchain right first pays off. If you are evaluating toolchains across languages rather than within OCaml, the [Julia development toolchain comparison](../2026-09-13-julia-development-toolchain-juliaup-pkg-revise-comparison/) makes an instructive parallel: a single blessed package manager removes an entire category of decision fatigue.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Dune vs Opam vs Esy in 2026: Which OCaml Build Toolchain Should You Actually Use?",
  "description": "A practical 2026 comparison of Dune, Opam and Esy for OCaml: real configuration files, CI recipes, decision matrix and migration pitfalls.",
  "datePublished": "2026-10-24",
  "dateModified": "2026-10-24",
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

### Is Dune a replacement for Opam?

No. Dune compiles code and runs tests; it does not download or install dependencies and it does not manage compiler versions. In a standard 2026 setup, Opam provisions the compiler and libraries, and Dune performs the build. You can use Dune without Esy, but a usable OCaml project essentially always uses Opam (or Esy) underneath.

### Can I use Dune and Esy at the same time?

Mechanically yes — Esy's build command is usually `dune build` — but you should not run both package managers against the same working directory. Esy installs into a project-local sandbox and exposes binaries through `esy x`; an Opam-installed `dune` on your `PATH` may resolve a different compiler. Pick Esy as the entry point and let it drive Dune.

### Which tool should a beginner learn first?

Dune plus Opam, in that order of daily usage. Nearly every OCaml tutorial, the official package index, and upstream `CONTRIBUTING.md` files assume this pair. Learning Esy first is a common cause of confusion because most documentation will not match what you see on screen.

### How do I reproduce an OCaml build exactly on CI?

Three steps: use the official `ocaml/opam` Docker images so the compiler matches, commit a lockfile (`opam lock` output or `esy.lock/`), and run everything through `opam exec --` so the shell environment is explicit. Add `dune build @fmt` as a check so formatting drift fails the build instead of silently rewriting files.

### Does this toolchain work for Windows developers?

Opam and Dune work on Windows, but the smoothest path in 2026 remains WSL2 with the official Linux images, especially when native C stubs or cross-compilation are involved. Esy's sandbox model is comparatively Windows-friendly for pure OCaml/Reason code, though native dependencies still vary by package.

### Why does `dune build` fail with "language version not supported"?

Your `dune-project` declares a newer `(lang dune X.Y)` than the installed `dune` binary supports. Either upgrade the binary (`opam update && opam upgrade dune`) or lower the declared version. In CI this almost always means the base image is stale — pin the image tag in your workflow file.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
