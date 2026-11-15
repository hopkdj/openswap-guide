---
title: "scopt vs decline vs Scallop in 2026: Which Scala CLI Parser Should You Ship?"
date: "2026-11-15"
draft: false
tags: ["scala", "cli", "developer-tools", "decline", "scopt"]
description: "A practical comparison of Scala's three main command-line parsing libraries — scopt, decline and Scallop — with real parser code, error handling behavior and migration traps."
cover: "/img/screenshots/scala-cli-parsers-cover.jpg"
---

Every Scala service eventually grows a command-line entry point, and the first ten minutes of that work decide how the next two years feel. Parse arguments with `args(0)` and you will be rewriting the whole thing when someone asks for `--dry-run`; pick a library casually and you inherit its error messages, its help output, and its opinions about subcommands forever. There are exactly three contenders that matter in 2026, and they are philosophically incompatible.

**scopt** is the veteran: a mutable-builder DSL that has shipped in Scala tooling since 2.10. **decline** is the functional one, built on Cats, where a parser is a value you compose. **Scallop** is the pragmatic one: you subclass a configuration class, declare options as fields, and call `verify()`. Choosing between them is not about features — all three parse `-n 5`, subcommands, and repeated flags. It is about which failure mode you can live with.

## TL;DR: Quick Verdict

**Use decline** if you already depend on Cats, want parsers as composable values, and care about help text that reads like a real Unix tool. **Use scopt** if you are maintaining an existing build (sbt plugins, older Spark jobs, internal tooling) or want the smallest possible conceptual surface with no functional-programming dependency. **Use Scallop** if you want flags declared as class fields and validated automatically at construction — it is the fastest path from zero to a working `--help`, at the cost of fighting its macro-ish DSL when options become conditional. Teams starting fresh in Scala 3 with no Cats dependency should still pick **scopt** over Scallop: the explicit `OParser` value is easier to test and refactor than a subclass whose constructor performs parsing.

## Head-to-Head Comparison (November 2026)

| Dimension | scopt | decline | Scallop |
|---|---|---|---|
| GitHub stars | **1,445** | **678** | **684** |
| Last commit | 2026-10-27 | 2026-04-08 | 2026-10-05 |
| Style | Builder DSL (functional or OO) | Composable values (Cats) | Subclass `ScallopConf` |
| Scala 3 support | Yes (4.x) | Yes | Yes |
| Cats dependency | No | **Yes** (`cats-core`) | No |
| Subcommands | `cmd("name")` with nested parsers | `Opts.subcommand(...)` | `Subcommand` objects |
| Repeated options | `unbounded()` / `minOccurs` | `Opts.options[A]` → `NonEmptyList` | `List[Int]` typed options |
| Default help output | Generated, customizable | Generated, high quality | Generated, very detailed |
| Error messages | String, `failure(...)` | Typed `Help`/`UsageError` | Exceptions / `verify()` |
| Validation hook | `.validate(...)` / `.checkConfig` | Refined/Cats combinators | `verify()` overrides |
| Config style | Case class + `copy` | Arbitrary result type | Mutable fields read via `conf.x()` |
| Best fit | Existing tooling, minimal deps | New FP-leaning codebases | Rapid internal tools |

Star counts, commit dates and release data were pulled from the GitHub API on 2026-11-15.

## Decision Matrix: Ten-Second Choice

| Your situation | Choose | Why |
|---|---|---|
| New Scala 3 CLI, no Cats in the build | **scopt** | Zero transitive deps, `OParser` is testable as a value |
| Already using Cats Effect / http4s | **decline** | Same abstractions, `Opts` composes with `Validated` |
| Internal admin tool, 6 flags, ship today | **Scallop** | Fields + `verify()` is the shortest working example |
| sbt plugin or Scala 2.12 legacy build | **scopt** | Longest track record on old Scala versions |
| Needs `--help` text polished for end users | **decline** | Best default formatting and `metavar` support |
| Config must be a validated immutable case class | **scopt** or **decline** | Scallop's model is mutable-by-construction |
| Multi-level nested subcommands | **Scallop** | Nested `Subcommand` objects are first-class |

## scopt: The Builder Everyone Inherits

scopt 4.x splits into two syntaxes over the same model: a functional DSL and an object-oriented DSL. Both start from a case class holding defaults, which is what makes scopt pleasant in tests — parsing is just a function from `Array[String]` to `Option[Config]`.

```scala
import java.io.File
case class Config(
    foo: Int = -1,
    out: File = new File("."),
    xyz: Boolean = false,
    libName: String = "",
    maxCount: Int = -1,
    verbose: Boolean = false,
    files: Seq[File] = Seq())

import scopt.OParser
val builder = OParser.builder[Config]
val parser1 = {
  import builder._
  OParser.sequence(
    programName("scopt"),
    head("scopt", "4.x"),
    opt[Int]('f', "foo")
      .action((x, c) => c.copy(foo = x))
      .text("foo is an integer property"),
    opt[File]('o', "out")
      .required()
      .valueName("<file>")
      .action((x, c) => c.copy(out = x))
      .text("out is a required file property"),
    opt[Unit]("verbose")
      .action((_, c) => c.copy(verbose = true))
      .text("verbose is a flag"),
    help("help").text("prints this usage text")
  )
}
```

Parsing returns an `Option`, and the pattern most teams settle on is a single match that exits non-zero on failure:

```scala
OParser.parse(parser1, args, Config()) match {
  case Some(config) => run(config)
  case _            => sys.exit(1)
}
```

Two scopt features earn their keep in real builds. `.unbounded()` on a `Seq` option allows repeated flags (`-j a.jar -j b.jar`), and `.checkConfig` runs cross-field validation after parsing, which is the clean place for rules like "`--max` requires `--libName`". The unavoidable weakness: scopt's errors are strings. There is no typed error channel, so callers cannot distinguish "unknown flag" from "file missing" without parsing text.

Subcommands exist (`cmd("run").action(...).children(...)`) and work fine, but nesting them three levels deep produces parser code that is hard to skim — a real consideration if you are wrapping `git`-style workflows.

## decline: Parsers as Values

decline is what you get when a parser is a value with a `Functor`/`Applicative` shape. Every option is an `Opts[A]`, and `mapN` combines them into your config type. That means a parser can be passed to a function, tested in isolation, and reused across commands without any ceremony.

```scala
import com.monovore.decline._
import java.nio.file.Path

val lines = Opts.option[Int]("lines", short = "n", metavar = "count",
  help = "Set a number of lines.")
val quiet = Opts.flag("quiet", help = "Don't print any metadata to the console.")
val file  = Opts.argument[Path](metavar = "file")
```

Repeated options and arguments map to `NonEmptyList`, which is exactly the type you want and rarely the type you remember to expect:

```scala
val settings = Opts.options[String]("setting", help = "Repeatable setting.")
val verbose  = Opts.flags("verbose", help = "Print extra metadata.")
val files    = Opts.arguments[String]("file")
```

Wrapping a parser into a runnable program is a single `Command`, and that command doubles as a subcommand elsewhere — the property that makes decline scale to tools with a dozen verbs:

```scala
val tailCommand = Command(
  name = "tail",
  header = "Print the last few lines of one or more files."
) {
  tailOptions
}

val tailSubcommand = Opts.subcommand(tailCommand)
// or, more concisely:
val tailSubcommand2 = Opts.subcommand("tail", help = "Print the few lines of one or more files.") {
  tailOptions
}
```

`Command(...).main(args)` handles `--help`, `--version`, and error rendering for you, and the failure path returns a typed `Help` or `UsageError` rather than throwing. The cost is honest: **decline requires cats-core**. If your build has no Cats and you only need three flags, that is 4 MB of transitive dependency for a nicer `Either`. Note also the maintenance signal in the table above — decline's last commit is April 2026, months behind scopt and Scallop. It is stable rather than abandoned, but do not expect rapid releases.

## Scallop: Declare Fields, Call verify()

Scallop inverts everything. You subclass `ScallopConf`, declare options as `val`s, and construction performs parsing; `verify()` enforces the constraints you declared.

```scala
import org.rogach.scallop._

class Conf(arguments: Seq[String]) extends ScallopConf(arguments) {
  val apples = opt[Int](required = true)
  val bananas = opt[Int]()
  val name = trailArg[String]()
  verify()
}

object Main {
  def main(args: Array[String]): Unit = {
    val conf = new Conf(args)
    println("apples are: " + conf.apples())
  }
}
```

That single class parses both long and short forms — `--apples 4 --bananas 10 strangeTree` and `-a 4 appleTree` both work — because Scallop derives short names from the field name. For a quick internal tool this is unbeatable: five lines, working help text, required-flag enforcement.

Scallop's party trick is its trailing-argument matching. Because it uses a backtracking parser, it can split `--files a b --files c d` into two separate lists without you writing a delimiter convention, and nested subcommands are plain objects:

```scala
object Conf extends ScallopConf(Seq("sub1", "sub2")) {
  object sub1 extends Subcommand("sub1") {
    val verbose = opt[Boolean]()
  }
  object sub2 extends Subcommand("sub2") {
    val level = opt[Int]()
  }
  addSubcommand(sub1)
  addSubcommand(sub2)
  verify()
}
```

The price shows up in two places. First, parsing happens in the constructor, so a "parse and then decide" flow requires catching `ScallopException` around object creation — awkward inside tests and impossible to compose. Second, values live behind `conf.apples()` accessors on a mutable object; converting to an immutable config case class is manual glue you write once per project. Teams that start with Scallop for a six-flag tool often migrate at flag twenty, and the migration is a rewrite of the CLI layer, not a refactor.

## Pitfalls That Bite in Production

**1. Negative numbers look like flags.** All three parsers treat `-5` as a potential option name. If your tool accepts a numeric argument that can be negative, require `--count=-5` or document the `--` terminator. Scallop handles this best by default; scopt needs explicit `opt[Int]` handling plus user discipline.

**2. `--` must be honored.** `tool -- --weird-filename` is the POSIX escape hatch. decline supports it through `Opts.arguments`; verify your chosen library does too before your CLI wraps another command (e.g., invoking `docker` or `ffmpeg`).

**3. Required flags inside optional subcommands.** Declaring `opt[String]("token", required = true)` at the top level of a Scallop config makes `tool --help` itself fail validation unless you guard with `verify()` after checking `conf.subcommand`. In scopt, place requirements inside the `cmd(...).children(...)` block instead.

**4. Help text is a compatibility surface.** Scripts and runbooks reference your flags. Once `--region` is public, renaming it breaks automation even if the library supports aliases. Add aliases with `.abbr`/`short` from day one.

**5. Native images and reflection.** If you ship a GraalVM `native-image` binary, Scallop's runtime reflection over `ScallopConf` subclasses needs explicit config, while scopt and decline are plain code and usually just work. This alone decides the choice for CLI tools distributed as single binaries.

**6. Testing strategy differs.** With scopt and decline you test a pure function (`OParser.parse` or `Command` internals). With Scallop you construct `new Conf(Seq("--apples", "4"))` and catch exceptions — workable, but slower and noisier in test output.

## A Minimal Build Setup

The dependency lines are boring but frequently wrong. With sbt:

```scala
libraryDependencies ++= Seq(
  "com.github.scopt"       %% "scopt"     % "4.1.0",
  "com.monovore"           %% "decline"   % "2.4.1",
  "org.rogach"             %% "scallop"   % "5.1.0"
)
```

And with Scala CLI, which is increasingly how small tools are shipped:

```bash
scala-cli run Main.scala --dep com.github.scopt::scopt:4.1.0 -- --foo 42
```

Version numbers move; pin them from each project's release page rather than copying a blog post — including this one.

## FAQ

**Which Scala CLI parser has the best help output?**
decline, by a small margin. Its `metavar` and `help` parameters produce conventional Unix-style output with aligned columns, and `Command(...).main` prints it consistently. Scallop's output is the most detailed (it lists every option with types), while scopt requires manual `head(...)` and `.text(...)` tuning to look polished.

**Can I use scopt with Scala 3?**
Yes — scopt 4.x is cross-published for Scala 3, and the `OParser` builder DSL works unchanged. The object-oriented DSL also compiles, though most new code uses the functional builder because it avoids subclassing.

**Does decline require Cats Effect?**
No. decline depends on cats-core only, not on any effect system. You can use it in a plain `main` method; the parser returns values and `Command.main` handles exiting. Teams on ZIO use decline without issue, though ZIO users sometimes prefer zio-cli for its tighter integration.

**How do I parse repeated flags into a Map?**
In scopt, `opt[Map[String, String]]("kwargs").valueName("k1=v1,...")` with a custom `.action` that splits on commas. In decline, use `Opts.options[String]("setting")` and fold the `NonEmptyList` yourself. Scallop supports `List[String]` typed options directly, then you map over them.

**Is Scallop's backtracking parser slow?**
No measurable difference at CLI scale. Backtracking matters for correctness on ambiguous trailing arguments, not for runtime: parsing a few dozen flags takes microseconds in all three libraries.

## Further Reading

For the HTTP layer that usually sits behind these tools, our [Scala HTTP client comparison](../2026-07-25-scala-http-clients-http4s-akka-http-sttp-zio-http/) covers http4s, Akka HTTP and sttp. If you are comparing CLI ergonomics across the JVM, the [Kotlin CLI framework guide](../2026-10-14-kotlin-cli-frameworks-clikt-kotlinx-cli-mordant/) — Clikt, kotlinx-cli and Mordant — is the closest direct analogue, and the [Swift CLI comparison](../2026-08-21-swift-cli-frameworks-argument-parser-swiftcli-consolekit-comparison/) shows how the same problem is solved outside the JVM.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "scopt vs decline vs Scallop in 2026: Which Scala CLI Parser Should You Ship?",
  "description": "Practical comparison of Scala command-line parsing libraries scopt, decline and Scallop, with real parser code, subcommand patterns, validation hooks and production pitfalls.",
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
