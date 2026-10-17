---
title: "gopls vs rust-analyzer vs clangd vs pyright in 2026: Which Language Server Actually Keeps Up?"
date: "2026-10-17"
tags: ["developer-tools", "language-server", "lsp", "gopls", "rust-analyzer", "clangd", "pyright"]
draft: false
description: "A practical comparison of gopls, rust-analyzer, clangd and pyright in 2026 — install commands, real config files, indexing behaviour, memory footprint, and which editor setups they suit."
---

Your editor feels slow and you blame the theme. It is almost never the theme. It is the language server: a background process that parses your repository, resolves types, and streams diagnostics over JSON-RPC. When it is healthy, go-to-definition is instant. When it is not, every keystroke queues behind a full re-index of a 400,000-line workspace.

Four servers dominate serious setups in 2026: **gopls** (Go, ships in `golang/tools`, 8,005 stars), **rust-analyzer** (16,913 stars), **clangd** (part of `llvm/llvm-project`, 41,092 stars), and **pyright** (15,685 stars). All four speak the Language Server Protocol, so the same server works in Neovim, VS Code, Emacs, Helix, or Zed. What differs is how they index, what they need from your build system, and how much RAM they will quietly consume.

## Quick Verdict

**gopls** is the only sane choice for Go and it earns that monopoly. **rust-analyzer** is the most sophisticated of the four but demands Cargo discipline and can spawn build scripts you did not expect. **clangd** is unbeatable on a project with a real `compile_commands.json` and miserable without one. **pyright** is the fastest to adopt and the least magical — it type-checks rather than fully indexes, which makes it cheap on huge repositories and weaker on dynamic code.

Choose by build system, not by language preference. The server that can read your build metadata will always beat the server that has to guess.

## Side-by-Side Comparison

| Dimension | gopls | rust-analyzer | clangd | pyright |
|---|---|---|---|---|
| **Language** | Go | Rust | C / C++ / Objective-C | Python |
| **Maintained by** | Go team (`golang/tools`) | Rust project | LLVM project | Microsoft |
| **Install** | `go install golang.org/x/tools/gopls@latest` | `rustup component add rust-analyzer` | `apt install clangd` / LLVM release | `npm i -g pyright` |
| **Needs build metadata** | No (reads `go.mod`/`go.work`) | Cargo (or `rust-project.json`) | Yes — `compile_commands.json` | No (reads `pyrightconfig.json` + venv) |
| **Indexing model** | Package-level, on demand | Full crate graph, persistent cache | Background index, persisted to disk | File-level type inference |
| **Type checking** | Compiler-grade | Compiler-grade | Compiler-grade | Static analysis, configurable strictness |
| **Typical RAM, mid-size repo** | 300-800 MB | 500 MB - 2 GB | 400 MB - 1.5 GB | 150-400 MB |
| **Config file** | editor settings (`gopls`) | `rust-analyzer.toml` / editor settings | `.clangd` (YAML) | `pyrightconfig.json` |
| **License** | BSD-3-Clause | MIT / Apache-2.0 | Apache-2.0 with LLVM exceptions | MIT |
| **GitHub stars (parent repo)** | 8,005 | 16,913 | 41,092 | 15,685 |
| **Last commit** | 2026-10-16 | 2026-10-17 | 2026-10-17 | 2026-10-16 |

## Decision Matrix

| Your setup | Pick | Why |
|---|---|---|
| Go services in a multi-module `go.work` | **gopls** | Native workspace support and `directoryFilters` for monorepos |
| Rust workspace, 30+ crates, heavy macros | **rust-analyzer** | Best macro expansion and trait resolution of any LSP server |
| C++ with CMake or Bazel | **clangd** | Uses the exact same flags as your compiler, so diagnostics match CI |
| Python monorepo with several virtualenvs | **pyright** | Per-directory config and cheap incremental checking |
| Constrained laptop, polyglot repo | **pyright + gopls**, skip clangd | clangd's background index is the first thing to evict memory |
| Kernel / Chromium-scale C++ | **clangd + remote index** | Local background indexing will not finish before lunch |

## gopls: The Go Team's Own Server

`gopls` is developed inside the Go tools repository and is the reference implementation of LSP for Go. It reads `go.mod`, `go.work`, and build tags directly, which means there is no separate index build step and no "compile database" to generate.

Install and verify:

```bash
go install golang.org/x/tools/gopls@latest
gopls version
gopls check ./...
```

Configuration is passed by the editor. In Neovim with the built-in LSP client:

```lua
vim.lsp.config('gopls', {
  settings = {
    gopls = {
      analyses = { unusedparams = true, shadow = true },
      staticcheck = true,
      directoryFilters = { "-node_modules", "-vendor", "-.git" },
      codelenses = { test = true, tidy = true, upgrade_dependency = true },
      completeUnimported = true,
      usePlaceholders = true,
    },
  },
})
```

`staticcheck = true` is the single highest-value flag; it pulls in a large set of additional analyzers that catch real bugs rather than style nits. `directoryFilters` is the difference between a usable and unusable experience in a monorepo that vendors dependencies.

The weak spot is memory on very large trees. `gopls` keeps package metadata for every workspace module it has loaded, and in a repository with hundreds of modules it will grow into the gigabyte range. The mitigation is workspace layout, not a flag: split `go.work`, or restrict the editor session to the module you are actually editing.

## rust-analyzer: Compiler Front-End as a Service

`rust-analyzer` is not a linter bolted onto a compiler. It is a full front-end with its own name resolution, macro expansion, and trait solver — which is why "go to definition" works through `macro_rules!` expansions that no text-based index could follow.

Install through rustup so the server version tracks your toolchain:

```bash
rustup component add rust-analyzer
rust-analyzer --version
```

Cargo projects work with no configuration. Non-Cargo builds need a `rust-project.json` describing crates, roots, and dependencies:

```json
{
  "crates": [
    {
      "display_name": "firmware",
      "root_module": "src/main.rs",
      "edition": "2024",
      "cfg": ["target_arch=\"thumbv7em\"", "feature=\"defmt\""]
    }
  ]
}
```

For anything with procedural macros, the relevant settings are about trust and cost:

```json
{
  "rust-analyzer.cargo.features": "all",
  "rust-analyzer.procMacro.enable": true,
  "rust-analyzer.check.command": "clippy",
  "rust-analyzer.cargo.buildScripts.enable": true,
  "rust-analyzer.cargo.targetDir": true
}
```

`check.command: clippy` makes diagnostics match what CI actually runs. `cargo.targetDir: true` gives the server its own target directory so it does not fight with your terminal builds for the same lock — a small setting that eliminates the "waiting for file lock on build directory" stall.

The security consideration is real: with build scripts enabled, opening a hostile Rust repository executes its `build.rs`. In an editor that auto-starts servers on folder open, that is remote code execution by design. Keep the setting off for repositories you have not reviewed.

## clangd: Excellent With a Compile Database, Useless Without One

`clangd` uses the same parser and semantic analysis as Clang, so its diagnostics match what `g++` or `clang++` will say at build time — as long as it receives the same flags. Those flags come from `compile_commands.json`.

Generate it from CMake:

```bash
cmake -S . -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
ln -sf build/compile_commands.json compile_commands.json
```

Or capture it from any build system with `bear`:

```bash
bear -- make -j$(nproc)
```

Then tune behaviour with a `.clangd` file at the repository root:

```yaml
CompileFlags:
  Add: [-std=c++23, -Wall]
  Remove: [-Werror, -fno-exceptions]
  CompilationDatabase: build
Diagnostics:
  ClangTidy:
    Add: [bugprone-*, performance-*, modernize-use-nullptr]
    Remove: [modernize-use-trailing-return-type]
Index:
  Background: Build
  StandardLibrary: Yes
```

`CompileFlags.Remove: [-Werror]` is the flag nobody tells you about. Without it, the editor inherits `-Werror` from CI and turns every warning into a red squiggle that blocks nothing in your editor but makes the file look broken.

Without a compile database, clangd falls back to heuristics — it will still parse headers and offer completions, but include paths will be wrong, and on a project with generated headers you will get a wall of false "file not found" diagnostics. If your build system cannot emit `compile_commands.json`, generate a minimal one by hand for the translation units you edit most; a partial database beats none.

## pyright: Type Checking Without the Index

`pyright` takes a different architectural bet. Instead of building a persistent project-wide index, it performs fast incremental type inference per file, pulling in imports as needed. That makes it dramatically lighter than clangd or rust-analyzer on large repositories, and it makes first-run latency almost nonexistent.

Install and configure:

```bash
npm install -g pyright
pyright --version
```

```json
{
  "include": ["src", "tests"],
  "exclude": ["**/node_modules", "**/.venv", "**/build"],
  "venvPath": ".",
  "venv": ".venv",
  "pythonVersion": "3.13",
  "typeCheckingMode": "standard",
  "reportMissingImports": "error",
  "reportMissingTypeStubs": "warning",
  "executionEnvironments": [
    { "root": "services/api", "extraPaths": ["services/shared"] }
  ]
}
```

`executionEnvironments` is what makes pyright viable in a monorepo: each service can have its own root and `extraPaths` instead of forcing one global `PYTHONPATH`. `typeCheckingMode: "standard"` is the right default for existing codebases; `"strict"` on a legacy repository produces hundreds of errors on day one and gets disabled by day three.

Where pyright loses is dynamism. Code that builds classes with `type()`, mutates `__dict__`, or imports through `importlib` will confuse any static checker, and pyright is no exception. The fix is targeted `# type: ignore` comments or per-file rule overrides, not switching to a heavier server — no Python language server resolves runtime metaprogramming reliably.

## Migration and Coexistence Notes

- **One server per language, not per editor.** If you run both Pylance (VS Code) and pyright CLI in CI, pin the same version, or you will chase diagnostics that only exist in one of them.
- **Persistent caches are worth the disk.** `rust-analyzer` and `clangd` both cache indexes on disk. Deleting the cache to "fix" slowness usually costs ten minutes of re-indexing for no benefit.
- **Index the code you edit.** In a monorepo, opening the repository root and expecting instant navigation across two million lines is not a server bug. Restrict the workspace, or use `directoryFilters` (gopls) and `exclude` (pyright).
- **Diagnostics on save versus on type.** `rust-analyzer`'s `checkOnSave` runs `cargo check`, which is correct but expensive on every keystroke. Set `checkOnSave` to `false` and run it on demand if you work on battery.
- **Editor config is not portable.** LSP settings live in editor-specific files. Keep a `.editorconfig` for whitespace and accept that server settings must be duplicated per editor — there is no cross-editor standard yet.

## Related Reading

For the parsing technology underneath these servers, our [parser generator and combinator comparison](../2026-06-20-parser-generator-combinator-libraries-antlr-treesitter-nom-pest-nearley/) explains the trade-offs between generated and hand-written parsers. The [Zig toolchain guide](../2026-09-14-zig-toolchain-zig-build-zls-zig-cc-guide/) covers `zls`, the same pattern applied to a younger language. And if you are choosing the editor that hosts these servers, the [Helix vs Neovim vs Kakoune comparison](../2026-09-01-helix-vs-neovim-vs-kakoune-modal-editor-comparison/) is the relevant read.

## FAQ

### Do I need a different language server for each editor?

No. Any LSP-compliant editor can drive gopls, rust-analyzer, clangd, or pyright. What changes is the configuration syntax and how the editor launches the process. The server binary is the same, which is why a Neovim setup and a VS Code setup can produce identical diagnostics.

### Why does clangd show errors that my build does not?

Almost always because it is using different flags. clangd reads `compile_commands.json`; if that file is stale or was generated from a different build directory, the flags diverge. Regenerate the database and confirm the `.clangd` file is not removing an include path your build needs.

### Is rust-analyzer slower than gopls?

On first index, yes — rust-analyzer builds a crate graph and expands macros, which takes minutes on a large workspace. After that it is comparable, and in incremental edits it is often faster because the index is persistent. gopls has no comparable cold-start penalty but pays continuously in memory on big module graphs.

### Can pyright replace mypy in CI?

For most projects, yes, with caveats. pyright is faster and has better incremental behaviour, but mypy has plugins (Django, SQLAlchemy) that pyright lacks. If your codebase depends on a mypy plugin for correct types, run mypy in CI and pyright in the editor, and accept that the two will occasionally disagree.

### How much RAM should I budget for a language server?

Assume 500 MB per active server on a mid-size repository, and 1-2 GB for clangd or rust-analyzer on large C++ or Rust workspaces. On an 8 GB laptop, running three servers plus a browser is the usual cause of swap thrash. Disable servers for languages you are not editing in the current session.

### Does gopls work without a `go.mod` file?

It works in GOPATH mode or in a directory with no module, but with degraded features: no workspace-wide analysis, and imports cannot be resolved reliably. If you are editing Go seriously, create the module first — this is a build-system prerequisite, not a server limitation.

## The Bottom Line

Language servers are infrastructure. You should notice them only when they break, and the way to keep them boring is to give each one the build metadata it expects: a `go.work` for gopls, a Cargo workspace for rust-analyzer, `compile_commands.json` for clangd, and a `pyrightconfig.json` with the right virtualenv for pyright. Do that and all four are excellent. Skip it and every one of them will feel broken in a different way.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "gopls vs rust-analyzer vs clangd vs pyright in 2026: Which Language Server Actually Keeps Up?",
  "description": "A practical comparison of gopls, rust-analyzer, clangd and pyright in 2026 — install commands, real config files, indexing behaviour, memory footprint, and which editor setups they suit.",
  "datePublished": "2026-10-17",
  "dateModified": "2026-10-17",
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
