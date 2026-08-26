---
title: "Haskell CLI Parsing in 2026: optparse-applicative vs optparse-generic vs cmdargs — Which Should You Use?"
date: "2026-08-26"
tags: ["haskell", "cli", "command-line", "library-comparison", "haskell-libraries"]
draft: false
cover: "/img/screenshots/optparse-cover.png"
---

Haskell has three serious command-line parsing libraries, and they embody three completely different philosophies: composition, derivation, and reflection. Choosing the wrong one is not fatal — but it determines whether your `--help` output is a pleasure to read, whether flags parse at compile time, and whether you can add a subcommand without touching the parser at all. After comparing **optparse-applicative**, **optparse-generic**, and **cmdargs** against real usage patterns, one clear winner emerges for new projects — and one library you should only touch if you are maintaining legacy code.

## TL;DR — Quick Verdict

**optparse-applicative is the default choice for new Haskell CLIs** — it is the most popular (959 GitHub stars), the only one with rich auto-generated help, sensible error messages, and bash completion, and its applicative style composes subcommands cleanly. **optparse-generic is the right pick for internal tools and scripts** where you want a parser for free from a plain record type. **cmdargs is in maintenance mode** — its author's own tooling has moved on, and the `Data`/`Typeable` machinery it depends on feels dated next to GHC's built-in `Generic` deriving. Only reach for it when a legacy codebase already uses it.

## At a Glance — The Comparison Table

All stats fetched live from GitHub on 2026-08-26.

| Criterion | optparse-applicative | optparse-generic | cmdargs |
|---|---|---|---|
| GitHub stars | 959 | 215 | 94 |
| Last push | 2026-06-27 | 2026-05-29 | 2025-02-02 |
| License | BSD-3-Clause | BSD-3-Clause | BSD-3 (GitHub: no SPDX tag) |
| Parser style | Applicative combinators | Generic derivation | Data/Typeable reflection |
| Boilerplate per flag | ~4 lines | 0 (derived) | 1 record field + derive |
| Auto `--help` | ✅ Excellent | ✅ Generated from type | ✅ Generated |
| Subcommands | ✅ First-class (`hsubparser`) | ✅ Auto from constructors | ✅ `cmdArgsMode` |
| Bash completion | ✅ Built-in | ❌ | ⚠️ Partial |
| Error messages | ✅ "Missing: --hello TARGET" style | ⚠️ Generic | ⚠️ Basic |
| Compile-time checking | ✅ Parser is a value | ✅ Types drive flags | ❌ Field names are strings |
| Maintenance status | ✅ Active | ✅ Stable, low-velocity | ⚠️ Maintenance mode |

## Use-Case Decision Matrix

| Use case | Recommended tool | Why |
|---|---|---|
| Production CLI tool users will actually type flags into | **optparse-applicative** | Best help text, clear errors, bash completion, battle-tested combinators |
| Internal script or one-off utility | **optparse-generic** | Zero parser code — derive `Generic`, call `getRecord`, ship it |
| Tool with complex subcommand tree (git-style) | **optparse-applicative** | `hsubparser` and `<**> helper` compose; constructors in optparse-generic also work but with less control |
| Legacy codebase already on cmdargs | **cmdargs** (keep) | Migration is not urgent; plan a phased rewrite, do not rip it out in a release |
| Library exposing CLI parsing to downstream users | **optparse-applicative** | Ecosystem standard; users know the `Parser` type, and completion support matters |
| Type-safe configuration with defaults baked in | **optparse-generic** | `Maybe` fields auto-become optional flags; `[]` auto-becomes repeated — behavior falls out of the type |

## optparse-applicative — The Composition-First Standard

optparse-applicative is the library almost every modern Haskell CLI uses, and its design is a masterclass in turning a parser into a first-class value. Instead of string-matching `argv`, you describe the interface with applicative combinators — `strOption`, `switch`, `argument`, `flag'` — and combine them with `<$>` and `<*>`. The README's Quick Start is the canonical example:

```haskell
import Options.Applicative

data Sample = Sample
  { hello      :: String
  , quiet      :: Bool
  , enthusiasm :: Int }

sample :: Parser Sample
sample = Sample
      <$> strOption
          ( long "hello"
         <> metavar "TARGET"
         <> help "Target for the greeting" )
      <*> switch
          ( long "quiet"
         <> short 'q'
         <> help "Whether to be quiet" )
      <*> option auto
          ( long "enthusiasm"
         <> help "How enthusiastic to be" )

main :: IO ()
main = greet =<< execParser opts
  where
    opts = info (sample <**> helper)
      ( progDesc "Print a greeting for TARGET"
     <> header "hello - a test for optparse-applicative" )

greet :: Sample -> IO ()
greet (Sample h False n) = putStrLn $ "Hello, " ++ h ++ replicate n '!'
greet _ = return ()
```

The payoff is in the generated UX. Run the program without `--hello` and you get `Missing: --hello TARGET` followed by a clean usage summary — not a panic. `helper` injects `--help` into any parser, `progDesc` and `header` build the help screen, and the same description powers **bash completion** out of the box. Because the parser is an applicative value, it composes: `optional`, `many`, and `hsubparser` let you build git-style command trees where each subcommand is its own `Parser`.

One quirk to know: `Parser` is *not* a `Monad`. Modern GHC lets you write do-notation via the **ApplicativeDo** extension, but the README warns that a few historical GHC 8.0.1 desugaring bugs bit `($)` applications — wrap `pure` results in parentheses if you hit strange compile errors.

## optparse-generic — The Zero-Boilerplate Derivation

optparse-generic, by Gabriella Gonzalez (the author of Dhall), takes the opposite approach: **the type is the CLI**. You define a record, derive `Generic`, write one `ParseRecord` instance, and `getRecord` hands you a fully working parser — flags, help text, and all:

```haskell
{-# LANGUAGE DeriveGeneric     #-}
{-# LANGUAGE OverloadedStrings #-}

import Options.Generic

data Example = Example { foo :: Int, bar :: Double } deriving (Generic, Show)

instance ParseRecord Example

main = do
    x <- getRecord "Test program"
    print (x :: Example)
```

That produces, with zero additional code:

```bash
$ stack runghc Example.hs -- --help
Test program

Usage: Example.hs --foo INT --bar DOUBLE

Available options:
  -h,--help                Show this help text
```

The magic is in how the library maps Haskell types onto CLI concepts — and this is where it gets genuinely clever:

- **Unlabeled fields** (e.g., `[String]` in the middle of a record) become positional arguments.
- **Multiple constructors** automatically generate subcommands — a sum type is a command tree.
- **`Maybe` fields** become optional flags/arguments.
- **`[]` fields** become repeated flags.
- **`Any`/`All`/`First`/`Last`/`Sum`/`Product`** all turn into repeated arguments with different aggregation semantics — `First` takes the first match, `Sum` adds them all.

For internal tools this is unbeatable: you get a typed CLI in one line, and the parser can never drift from the data type because the type *is* the specification. The trade-offs: less control over help text formatting, no bash completion, and the README's own honest caveat — "I expect this library's API to be reasonably stable, but only time will tell." If you need exotic types, you will have to write `ParseField`/`ParseFields`/`ParseRecord` instances by hand.

## cmdargs — The Legacy Reflection Approach

cmdargs is Neil Mitchell's library (yes, the HLint author), and for years it was *the* Haskell CLI answer. Its approach predates modern `Generic` deriving: you declare a record, derive `Data` and `Typeable`, and the library reflects over the type at runtime to figure out the flags:

```haskell
{-# LANGUAGE DeriveDataTypeable #-}
{-# OPTIONS_GHC -fno-cse #-}
module Sample where
import System.Console.CmdArgs

data Sample = Sample {hello :: String}
              deriving (Show, Data, Typeable)

sample = Sample{hello = def}

main = print =<< cmdArgs sample
```

The result is a working CLI where `--hello=world` parses into the record, `--version` prints "The sample program", and `--help` generates a usage screen. cmdargs also pioneered the "mode" system — `cmdArgsMode` gives you subcommands (HLint's `--report`, `--colour`/`-c` aliases, and underscore-to-hyphen flag translation all come from this library, and its README documents them with real HLint code).

**The honest assessment for 2026**: cmdargs works, but it is in maintenance mode — the last push was February 2025 and it is mostly upkeep. The `-fno-cse` GHC pragma it needs is a smell; field-name-to-flag mapping is stringly-typed rather than type-driven; and its reflection approach can't give you the compile-time guarantees of the other two. If you maintain a tool that already uses cmdargs, keep it — but budget a slow migration toward optparse-applicative, the same direction the ecosystem took a decade ago.

## Pitfalls and Migration Notes

- **You cannot use `Monad` operations inside optparse-applicative parsers.** No `if` on previous results, no `>>=`. Use `ApplicativeDo` for do-syntax, or restructure — the applicative limitation is what makes parsers composable and testable.
- **"Optional" in optparse-applicative means "has a default".** A `strOption` without a default is mandatory and errors with `Missing: --hello TARGET`. If you want truly optional flags, use `optional` or wrap the field in `Maybe`.
- **optparse-generic's type mapping surprises teams.** A `Maybe String` field means "flag optional"; a plain `String` means "required". If you put a `Maybe` in the middle of a record expecting positional handling, you get a positional *argument*, not a flag — read the type-conversion rules before designing your record.
- **cmdargs and GHC options.** The `-fno-cse` pragma in the hello-world example is required because GHC's common-subexpression elimination would otherwise evaluate attributes the wrong number of times. Copy the pragma when you copy the pattern.
- **`Generic` vs `Data`/`Typeable` is not just style.** optparse-generic's derivation runs at compile time and cannot fail at runtime; cmdargs reflects over `Data` and can behave unpredictably with unusual types. For a library that others embed, prefer the compile-time approach.
- **Pin your GHC and dependency versions in CI.** All three libraries track GHC releases closely; a `stack` or `cabal` freeze file prevents "works on my laptop" breakage. The Haskell ecosystem's dependency hygiene is a whole topic of its own, which our [Haskell web frameworks comparison](../2026-07-21-haskell-web-frameworks-yesod-scotty-servant/) touches on, alongside the testing story in our [Haskell testing frameworks guide](../2026-08-01-haskell-testing-frameworks-hspec-quickcheck-tasty-hunit/).
- **Compare across ecosystems before you commit.** Rust's clap, Ruby's Thor, and Python's click all made the same architectural bet optparse-applicative made — declarative parser descriptions. Our [Rust CLI parsers comparison](../2026-08-10-rust-cli-parsers-clap-argh-bpaf/) and [Ruby CLI frameworks guide](../2026-08-12-ruby-cli-frameworks-thor-commander-gli-comparison/) show the same trade-offs in those languages.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Haskell CLI Parsing in 2026: optparse-applicative vs optparse-generic vs cmdargs — Which Should You Use?",
  "description": "In-depth comparison of Haskell command-line parsing libraries — optparse-applicative, optparse-generic, and cmdargs — with real code examples, live GitHub stats, pitfalls, and a use-case decision matrix.",
  "datePublished": "2026-08-26",
  "dateModified": "2026-08-26",
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

**Q: Which Haskell CLI library should I use for a new project in 2026?**
A: optparse-applicative. It is the most popular (959 stars), actively maintained (last push June 2026), produces the best help text and error messages, supports subcommands and bash completion, and is the ecosystem standard most Haskell developers already know.

**Q: Does optparse-generic support subcommands?**
A: Yes — automatically. A data type with multiple constructors generates a subcommand tree with zero parser code. The trade-off is less control over help output and no bash completion support.

**Q: Is cmdargs still maintained?**
A: In maintenance mode only. The last push was February 2025, and the library's reflection-based design predates modern `Generic` deriving. Existing users should plan a gradual migration to optparse-applicative rather than starting new work on cmdargs.

**Q: Can I use do-notation with optparse-applicative?**
A: Yes, with the ApplicativeDo extension in modern GHC — `Parser` is an `Applicative` but not a `Monad`. Older GHC versions had desugaring bugs affecting `($)` inside ApplicativeDo blocks; wrap `pure` results in parentheses if you hit them.

**Q: Which library gives the most compile-time safety?**
A: optparse-generic, because the CLI is derived from the record type at compile time — flags cannot drift from the data model. optparse-applicative gives strong safety through typed `Parser` values, while cmdargs maps field names to flags as strings at runtime.

**Q: Are these libraries compatible with Stack and Cabal?**
A: All three are on Hackage and work with both Stack and Cabal. optparse-generic's README uses `stack build` / `stack runghc` in its examples, and optparse-applicative is a dependency of many major packages, so it resolves cleanly in either toolchain.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
