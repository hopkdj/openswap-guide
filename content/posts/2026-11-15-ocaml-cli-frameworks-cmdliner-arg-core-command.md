---
title: "OCaml CLI Parsing in 2026: Cmdliner vs Core.Command vs Arg — Which One Survives a Real Tool?"
date: "2026-11-15"
description: "Cmdliner, Core.Command and the stdlib Arg module compared on real OCaml code: man page generation, subcommands, exit codes, testability and dependency weight."
tags: ["ocaml", "cli", "developer-tools", "cmdliner"]
cover: "/img/screenshots/ocaml-cli-frameworks.jpg"
draft: false
---

Every OCaml tool starts the same way: a quick `Arg.parse` that takes twenty lines and works fine. Eighteen months later that tool has subcommands, environment-variable fallbacks, a `--json` output mode, and a `--help` page nobody has read since the first commit. The argument parser you picked on day one is now the reason your users cannot discover a flag that has existed for a year.

OCaml has three serious answers to this problem, and they are not interchangeable. **Cmdliner** treats the command line as a declarative value and generates man pages from it. **Core.Command** brings Jane Street's conventions, `let%map_open` syntax and shell completion. **Arg**, shipped with the compiler, is the smallest and most direct option. This article compares them with code you can actually compile, on the axes that matter: help output, subcommand structure, exit codes, testability and dependency weight.

**TL;DR:** Use **Cmdliner** for anything you will ship to other people — it produces real man pages, handles exit codes correctly, and has zero dependencies. Use **Core.Command** only if you already depend on Jane Street's `core`; the parser is good but the dependency tree is enormous. Use **Arg** for internal scripts under 200 lines where nobody will ever type `--help` twice.

## The Contenders at a Glance

| | **Cmdliner** | **Core.Command** | **Arg (stdlib)** |
|---|---|---|---|
| **Repository** | `dbuenzli/cmdliner` | `janestreet/core` | `ocaml/ocaml` |
| **Stars** | 347 | 1,362 | 6,636 (compiler) |
| **Last push** | 2026-10-18 | 2026-11-03 | 2026-11-14 |
| **License** | ISC | MIT | LGPL-2.1 with linking exception |
| **Dependencies** | None | `core`, `core_unix`, `ppx_let` | None (part of stdlib) |
| **Install** | `opam install cmdliner` | `opam install core core_unix` | already available |
| **Man page generation** | Yes, from term metadata | No (help text only) | No |
| **Shell completion** | Handled by the library | Generated from command shape | None |
| **Subcommands** | `Cmd.group`, arbitrary nesting | `Command.group`, arbitrary nesting | Manual dispatch |
| **Testability** | `Cmd.eval'` returns an int | `Command_unix.run` exits | `Arg.parse_argv` on an array |
| **Env-var fallback** | `Arg.env_var` | `~env` on flags | Manual `Sys.getenv` |

Star counts mislead here: the compiler repository's count reflects the language, not the `Arg` module, and Cmdliner's 347 stars understate it because it has been the default in the OCaml ecosystem for a decade.

## Decision Matrix: Pick by Use Case

| Your situation | Pick | Why |
|---|---|---|
| Public CLI with flags, env vars and a `--version` | **Cmdliner** | Man pages, exit codes and error messages are generated for you |
| Multi-command tool (`tool serve`, `tool migrate`, `tool doctor`) | **Cmdliner** | `Cmd.group` nests cleanly and `--help` works per command |
| You already use `core` for the rest of the codebase | **Core.Command** | Consistent style with the rest of your code; `let%map_open` reads well |
| You want shell completion generated from the command shape | **Core.Command** | Built into `Command` via `Command_unix` |
| A 100-line script in a repo nobody else runs | **Arg** | Zero dependencies, zero abstraction, done in ten minutes |
| Distroless/minimal container where every library matters | **Cmdliner** or **Arg** | No transitive `core` tree; Cmdliner is a single package |
| You need to unit-test argument parsing | **Cmdliner** | `Cmd.eval'` returns an exit code instead of calling `exit` |
| Legacy code already on `Arg.parse` | **Arg** | Migrating to Cmdliner is a rewrite, not a refactor |

## Cmdliner: Declarative Arguments and Free Man Pages

Cmdliner's README states the design in one line: it provides "a simple and compositional mechanism to convert command line arguments to OCaml values and pass them to your functions", and the module "automatically handles command line completion, syntax errors, help messages and UNIX man page generation." No dependencies, ISC licensed, installed with a single `opam install cmdliner`.

The modern API centres on `Cmd.info`, `Cmd.make`/`Cmd.v` and the applicative `Term` combinators. Here is a complete, compilable tool:

```ocaml
open Cmdliner

let file =
  let doc = "File to count lines in." in
  Arg.(required & pos 0 (some file) None & info [] ~docv:"FILE" ~doc)

let verbose =
  Arg.(value & flag & info ["v"; "verbose"] ~doc:"Report per-file counts.")

let run verbose file =
  let lines = In_channel.with_open_bin file In_channel.input_lines in
  let n = List.length lines in
  if verbose then Printf.printf "%s: %d lines\n" file n
  else Printf.printf "%d\n" n;
  Cmd.Exit.ok

let cmd =
  let doc = "count lines in a file" in
  Cmd.v (Cmd.info "linecount" ~version:"1.0.0" ~doc)
    Term.(const run $ verbose $ file)

let () = exit (Cmd.eval cmd)
```

Three details are worth pausing on. `Arg.file` is a typed converter, so the value arrives as a validated filename rather than a raw string, and a typo produces a proper error message instead of an exception. `Cmd.Exit.ok` returns `0` explicitly, which matters because Cmdliner maps your return value onto the process exit status. And `~version:"1.0.0"` gives you `--version` for free.

Subcommands follow the same shape. This is the structure the library's own `rm` example uses — `Arg.(non_empty & pos_all file [] & info [] ~docv:"FILE")` for a variadic positional argument, and `Cmd.make` for the command itself:

```ocaml
open Cmdliner

let files =
  Arg.(non_empty & pos_all file [] & info [] ~docv:"FILE" ~doc:"Files to remove.")

let yes =
  Arg.(value & flag & info ["y"; "yes"] ~doc:"Do not prompt.")

let rm files yes = (* ... *) Cmd.Exit.ok

let rm_cmd =
  Cmd.v (Cmd.info "rm" ~doc:"remove files") Term.(const rm $ files $ yes)

let serve_cmd =
  Cmd.v (Cmd.info "serve" ~doc:"start the daemon") Term.(const (fun () -> Cmd.Exit.ok) $ const ())

let main =
  Cmd.group (Cmd.info "tool" ~version:"1.0.0" ~doc:"Example multi-command tool")
    [rm_cmd; serve_cmd]

let () = exit (Cmd.eval main)
```

The payoff is the help output. `tool --help` prints usage, arguments and options; `tool rm --help` prints the subcommand's own page; `tool --help=plain` emits a roff man page you can ship in a package. That last flag is the reason Cmdliner wins for anything distributed through opam or a Linux distribution: you do not write the man page, and it cannot drift from the code because both come from the same metadata.

Cmdliner also supports environment-variable fallbacks with `Arg.env_var`, custom converters via `Arg.conv`, and `Arg.info ~docs:"OPTIONS"` to group flags into man page sections. Dependency order matters: `Term.(const run $ verbose $ file)` applies arguments left to right, so `run`'s parameters must be in the same order as the `$` chain.

## Core.Command: Jane Street Conventions, Jane Street Weight

`Command` lives in Jane Street's `core` (1,362 stars, pushed 2026-11-03). It is a solid parser with a distinctive style: commands are built with `Command.basic`, arguments are bound with the `let%map_open` ppx, and execution goes through `Command_unix.run` from `core_unix`.

```ocaml
open Core

let file =
  Command.Param.anon ("file" %: string)

let command =
  Command.basic
    ~summary:"Count the lines in a file"
    (let open Command.Let_syntax in
     let%map_open file = file in
     fun () ->
       let n = In_channel.read_lines file |> List.length in
       printf "%d\n" n)

let () = Command_unix.run command
```

Grouping commands is equally direct:

```ocaml
let () =
  Command_unix.run
    (Command.group ~summary:"Developer toolbox"
       [ "count", command
       ; "serve", serve_command ])
```

What you get in exchange for the dependency: consistent naming conventions across every Jane Street tool, generated bash completion, `-help` output that includes flag documentation and default values, and `Command.Param` composition that scales to a dozen flags without the parenthesised `$` chains you write in Cmdliner. The `let%map_open` style is genuinely more readable when a command has eight parameters.

What you pay: `core` plus `core_unix` plus `ppx_let`, which is a large dependency tree for a small binary. In a minimal container this can add tens of megabytes and a slow first build. If your project already uses `core` throughout, that cost is already sunk and `Command` is the natural choice. If you are writing a standalone utility, pulling in `core` only to parse four flags is hard to justify.

Two version details that trip people up: `Command_unix.run` comes from `core_unix`, not `core`, so the dune stanza must list both; and `Command.basic`'s summary is a single line — long descriptions go in `~full_expander` or the readme field, not into the summary.

## Arg: The Stdlib Module That Refuses to Grow Up

`Arg` ships with the compiler (6,636 stars on `ocaml/ocaml`, pushed 2026-11-14) and has not changed its philosophy since the 1990s: an associative list of specs, an anonymous-argument callback, and a usage string.

```ocaml
let files = ref []
let verbose = ref false
let output = ref "-"

let speclist = [
  ("-v", Arg.Set verbose, "Enable verbose logging");
  ("-o", Arg.Set_string output, "Write output to FILE (default: stdout)");
]

let anon_fun filename = files := filename :: !files
let usage = "usage: linecount [-v] [-o FILE] FILE..."

let () =
  Arg.parse speclist anon_fun usage;
  if !files = [] then begin
    prerr_endline "linecount: no input files";
    exit 2
  end
```

That is the whole API surface most people need: `Arg.Set`, `Arg.Set_string`, `Arg.Int`, `Arg.String` with a callback, and `Arg.align` to make the help output line up in columns. It costs nothing, adds no dependency, and works in any OCaml version.

The limits are structural, not cosmetic. There are no subcommands — you dispatch on `Sys.argv.(1)` yourself and lose `--help` per command. There is no man page generation, no shell completion, and no environment-variable binding. Error handling is `Arg.Bad` and `Arg.Help` exceptions, which means `Arg.parse` calls `exit` inside the parser: unit-testing the argument handling requires `Arg.parse_argv` with a hand-built array, and any side effect in your spec callbacks runs during parsing. For a script under 200 lines, none of that matters. For a distributed tool, all of it does.

## Wiring It Up With Dune

All three work with the same build system. A minimal project for the Cmdliner version:

```
; dune-project
(lang dune 3.16)
```

```
; bin/dune
(executable
 (name linecount)
 (public_name linecount)
 (libraries cmdliner))
```

For Core.Command, replace the library list:

```
(executable
 (name linecount)
 (public_name linecount)
 (preprocess (pps ppx_let))
 (libraries core core_unix.command_unix))
```

And install from opam:

```bash
opam install cmdliner
opam install core core_unix ppx_let
```

If you are still setting up the toolchain itself, our [OCaml build toolchain guide](../2026-10-24-ocaml-build-toolchain-dune-opam-esy-guide/) covers the dune/opam/esy decision, and the [concurrency comparison](../2026-09-12-ocaml-concurrency-lwt-vs-eio-vs-async/) matters here because both Cmdliner and Core.Command must stay off the event loop — argument parsing is synchronous by design, and a long-running command should hand off to Eio or Lwt after the term returns.

## Testing Your CLI Without Forking a Process

The ability to test argument parsing is where these libraries diverge most in practice.

With Cmdliner, use `Cmd.eval'` instead of `Cmd.eval`. The former returns the exit code as an `int` and does not call `exit`, so you can assert on it:

```ocaml
let () =
  let argv = [| "linecount"; "--verbose"; "README.md" |] in
  let code = Cmd.eval' ~argv cmd in
  assert (code = Cmd.Exit.ok)
```

That single change is why Cmdliner tools tend to have tests for their error paths — missing required argument, unknown flag, bad converter input — without shelling out.

With Core.Command, `Command_unix.run` exits the process, so tests usually invoke the built binary or call the underlying function directly and skip the parser. That is acceptable but leaves the mapping from flags to values untested.

With Arg, `Arg.parse_argv` takes an explicit array and is testable, but it still raises `Arg.Bad`/`Arg.Help` rather than returning a result, so every test needs exception handling. It works; it is simply more ceremony than the other two.

## Pitfalls and Migration Notes

- **Do not put side effects in Cmdliner terms.** Terms are evaluated before your function runs; printing or connecting to a database inside `Term.(const ...)` executes even for `--help`. Keep terms pure and do the work in the function they build.
- **`Cmd.eval` versus `Cmd.eval'`.** `Cmd.eval` exits the process. If you call it from a library function, your tests and your embedding application both lose control flow.
- **Return `Cmd.Exit` values, not arbitrary ints, from Cmdliner commands.** `Cmd.Exit.some_error` (123) and `Cmd.Exit.cli_error` (124) are conventional; returning `1` for a usage error breaks the expectation that usage problems are distinguishable from runtime failures.
- **Arg's spec callbacks run at parse time.** A callback that opens a file will open it while parsing, before validation is complete. Store the value in a ref and act after `Arg.parse` returns.
- **`Arg.parse` ignores unknown positional arguments unless you handle them.** `anon_fun` is called for every non-flag argument, including typos that look like filenames. Validate `!files` afterwards, as the example above does.
- **Core.Command needs `core_unix` for `Command_unix`.** Listing only `core` in dune gives an unbound module error that reads like a version mismatch.
- **Cmdliner man page sections are opt-in.** Without `~man` and `Arg.info ~docs:"..."` groups, `--help=plain` emits a thin page. Add sections early; retrofitting documentation into forty flags is the same work you were avoiding.
- **Version strings are yours to supply.** `~version:"1.0.0"` is a literal. Generate it from dune's `%%VERSION%%` substitution or it will lie after the first release.

## Which Should You Actually Use?

For anything another person will run, **Cmdliner**. Not because the parser is faster — all three are fast enough that parsing never appears in a profile — but because help output, man pages, exit codes and testability are the parts of a CLI that users judge, and Cmdliner generates all four from one declaration. The 347 stars understate its adoption; it is the parser behind `odig`, `opam`'s own tooling, and a large share of the OCaml CLI ecosystem.

Choose **Core.Command** when `core` is already in your dependency graph. The `let%map_open` binding style is the most readable of the three for commands with many flags, and generated completion is a real convenience. Do not adopt `core` for the parser alone.

Choose **Arg** when the tool is genuinely small and internal, or when you cannot take any dependency at all — a single-file script, a build helper, a container entrypoint. It will not scale to subcommands, but a 150-line script does not need to.

The migration path that actually works: start with `Arg` in a script, and when the third flag lands, rewrite the front end in Cmdliner while keeping the function it calls untouched. The function signature is the contract; the parser is replaceable. Also worth reading alongside this: our [OCaml web framework comparison](../2026-09-04-ocaml-web-frameworks-dream-opium-ocsigen-comparison/), since Dream and Opium both build their CLIs on Cmdliner.

## FAQ

### Is Cmdliner still maintained in 2026?

Yes. `dbuenzli/cmdliner` was last pushed in October 2026 and is actively maintained by its original author. It has no dependencies, which is why it has survived multiple OCaml ecosystem shifts without breaking.

### Does Cmdliner really generate man pages?

Yes. Your program's `--help=plain` option emits a roff man page built from the same `Cmd.info` and `Arg.info` metadata used for `--help`. Distributions package that output instead of a hand-written man page, and it stays correct because it is derived from the code.

### Why does Core.Command require core_unix?

`Command_unix` — the module exposing `Command_unix.run` — lives in `core_unix` because running a command touches process-level concerns: argv, exit status and the scheduler. `core` alone provides the `Command` module but not the runner, so dune must list both libraries.

### Can I use Arg and Cmdliner in the same program?

Technically yes, but do not. Mixing two parsers means two `--help` behaviours, two error formats and two exit-code conventions. Pick one per binary; Cmdliner can wrap a legacy `Arg`-based function between commands if you need a staged migration.

### Which library is fastest at startup?

The differences are in microseconds and irrelevant next to process startup. The meaningful cost is dependency weight: Cmdliner and Arg add no transitive libraries, while Core.Command pulls `core`, `core_unix` and `ppx_let`, which affects build time and binary size far more than parse time.

### How do I add environment-variable fallbacks?

Cmdliner does it declaratively with `Arg.env_var "MYTOOL_TOKEN"`, applied to an option's `Arg.info`. Core.Command supports `~env` on flag definitions. With `Arg` you read `Sys.getenv_opt` yourself, which also means you choose the precedence order manually.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "OCaml CLI Parsing in 2026: Cmdliner vs Core.Command vs Arg",
  "description": "Comparison of Cmdliner, Jane Street Core.Command and the stdlib Arg module for OCaml command line tools: man pages, subcommands, exit codes and testability.",
  "datePublished": "2026-11-15",
  "dateModified": "2026-11-15",
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
