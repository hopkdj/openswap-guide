---
title: "Ruby CLI Development in 2026: Thor vs Commander vs GLI — Build a Command-Line Tool Users Actually Love"
date: "2026-08-12"
tags: ["ruby", "cli", "developer-tools", "command-line"]
draft: false
---

Every serious engineering team ends up with a pile of internal command-line tools: deployment scripts, database migration runners, report generators, admin utilities. And every one of those tools starts the same way — with `OptionParser` and a `case` statement that grows until nobody dares touch it. Ruby's answer to this has always been a small galaxy of CLI frameworks, and in 2026 the choice has effectively narrowed to three: Thor, the Rake-like workhorse that powers Rails generators, Bundler, and Vagrant; Commander, the DSL-driven library that models itself on high-end user-facing CLIs; and GLI, the git-style subcommand parser built for deeply nested command structures. Picking the right one determines whether your tool is a joy to maintain or a source of dread for the next three years. This guide compares them with real code from the official repositories and documentation.

## TL;DR / Quick Verdict

**Choose Thor (5,264 stars, MIT) for anything that will live inside the Ruby ecosystem** — Rails, Bundler, and Vagrant all use it, so its conventions are familiar, its generator capabilities are unmatched, and its maintenance is guaranteed by the Rails core team. **Choose Commander (821 stars) when you are building a polished, user-facing CLI where help text, colors, and interactive output matter more than deep nesting.** **Choose GLI (1,274 stars, Apache 2.0) only when you genuinely need git-style nested subcommands with per-command options** — it is the most powerful parser of the three, but its development has slowed since 2025. For 90% of Ruby CLI projects in 2026, Thor is the safe, boring, correct choice.

## Quick Comparison Table

| Criterion | Thor | Commander | GLI |
|---|---|---|---|
| **GitHub stars** | 5,264 | 821 | 1,274 |
| **Last update** | Jul 2026 | Aug 2026 | Mar 2025 |
| **Style** | Class-based with `desc`/`method_options` | DSL with `command` blocks | DSL with `desc`/`command` + global options |
| **Subcommand nesting** | Via `subcommand` / `Thor::Group` | Flat commands | Deep nesting, git-style |
| **Automatic help** | Yes (`thor help`) | Yes (`--help`) | Yes (`help` command) |
| **Generators** | First-class (`Thor::Group`) | No | No |
| **Default values / types** | `method_options` typed | `c.option` typed | Flags, switches, arguments |
| **Zero runtime deps** | No (uses open-uri conventions) | Yes | Yes |
| **Used by** | Rails, Bundler, Vagrant | Chef (historically) | Internal tools, gem CLIs |
| **License** | MIT | MIT | Apache 2.0 |

## Decision Matrix: Which One for Your Case?

| Use Case | Recommendation | Why |
|---|---|---|
| Gem with a CLI that other Rubyists install | **Thor** | Rails ecosystem conventions; users already know `--help` behavior |
| Rails generator or code scaffolding task | **Thor** | `Thor::Group` and actions were built exactly for this |
| Internal ops tool with 2-5 flat commands | **Thor** | Minimal boilerplate, familiar syntax, huge community |
| Polished user-facing CLI (colors, progress bars) | **Commander** | `say`, colors, and high-touch output are first-class |
| CLI with nested subcommands like `tool remote add` | **GLI** | Deep nesting and per-command options without repetition |
| Script you will throw away in a month | **Neither** | Use `OptionParser`; a framework is overhead you do not need |
| Tool needing zero runtime dependencies | **GLI or Commander** | Both advertise zero runtime deps |

## Thor — The Rails-Ecosystem Workhorse

Thor is a toolkit for building powerful command-line interfaces, maintained by the Rails core team and used by Rails itself, Bundler, and Vagrant. Its design philosophy is "Rake, but for command-line apps": you write a plain Ruby class, annotate methods with `desc` and `method_options`, and Thor turns them into commands with automatic help, option parsing, and error handling. Because it powers Rails generators, it also ships a rich set of file-manipulation actions — `create_file`, `inject_into_file`, `template` — that make it the only real choice for scaffolding tools.

The official wiki's basic usage shows the pattern:

```ruby
class App < Thor
  package_name "App"
  map "-L" => :list

  desc "install APP_NAME", "install one of the available apps"
  method_options :force => :boolean, :alias => :string
  def install(name)
    user_alias = options[:alias]
    if options.force?
      # do something
    end
  end

  desc "list [SEARCH]", "list all of the available apps, limited by SEARCH"
  def list(search = "")
    # list everything
  end
end
```

Thor maps the method names to commands automatically:

```bash
thor app:install myname --force
# becomes App.new.install("myname") with {'force' => true} in options
```

For generators, `Thor::Group` runs multiple tasks in sequence and supports `argument` declarations, which is how Rails' `rails generate model User` works under the hood. Installation is a single line — `gem install thor` — and the API has been stable for over a decade, which is exactly what you want in an internal tool that will outlive three team reorganizations. The documented caveat is real, though: Thor is designed as a system tool for file and URL access and relies on open-uri conventions, so it should not receive unvalidated application user input — keep untrusted input handling in your own code.

## Commander — The Polished User-Facing CLI

Commander's goal is stated in its README: "The complete solution for Ruby command-line executables." Where Thor is a class-based toolkit, Commander is a DSL that reads like a specification for your CLI: you declare the program name, version, and description, then define each command with its syntax, description, and options in one block. It also integrates high-touch output helpers like `say` with color support and progress indicators — the kind of polish that makes a CLI feel like a product rather than a script.

The classic style from the official README:

```ruby
require 'commander/import'

program :name, 'Foo Bar'
program :version, '1.0.0'
program :description, 'Stupid command that prints foo or bar.'

command :foo do |c|
  c.syntax = 'foobar foo'
  c.description = 'Displays foo'
  c.action do |args, options|
    say 'foo'
  end
end

command :bar do |c|
  c.syntax = 'foobar bar [options]'
  c.description = 'Display bar with optional prefix and suffix'
  c.option '--prefix STRING', String, 'Adds a prefix to bar'
  c.option '--suffix STRING', String, 'Adds a suffix to bar'
  c.action do |args, options|
    options.default :prefix => '(', :suffix => ')'
    say "#{options.prefix}bar#{options.suffix}"
  end
end
```

There is also a modular style that keeps Commander out of the global namespace by including `Commander::Methods` in your own class — the recommended approach for libraries. Commander's weakness is structural: commands are flat, there is no first-class nesting, and the project's velocity is modest. But for a CLI that humans interact with directly — think `gh`-style tools before they grew subcommand trees — Commander's ergonomics are excellent.

## GLI — Git-Style Deep Subcommands

GLI (Git-Like Interface) exists to solve one problem precisely: building command-line apps that behave like `git`, with deeply nested subcommands where each level can have its own options. Ruby's built-in OptionParser makes this painful, and most frameworks flatten the tree. GLI wraps OptionParser and adds a global-options/command-options split, automatic help generation, and a scaffolding generator that produces a complete, tested project in seconds.

The official README shows the scaffold workflow:

```bash
gem install gli
gli init todo list add complete
cd todo
bundle exec bin/todo help
# NAME
#     todo - Describe your application here
#
# SYNOPSIS
#     todo [global options] command [command options] [arguments...]
#
# COMMANDS
#     add      - Describe add here
#     complete - Describe complete here
#     list     - Describe list here
```

GLI's help output is genuinely complete: global options, per-command options, and per-command synopses are generated from your declarations, which means documentation cannot drift from implementation. It has zero runtime dependencies, and its API has been stable for years. The trade-offs: development has slowed (last push March 2025), the project is a one-maintainer operation, and for simple flat CLIs the extra ceremony of global vs. command options is pure overhead. If your tool genuinely needs `tool remote add origin`-style nesting, GLI is still the best Ruby answer — just budget for maintaining it yourself if the maintainer ever steps away.

## Pitfalls and Migration Notes

**Do not let `method_options` default values bite you.** In Thor, `options[:alias]` returns the default when unset — but booleans declared with `:boolean` give you `options.force?` as a predicate. Mixing the two styles in one command is the most common source of subtle bugs in real Thor codebases. Decide per command and be consistent.

**Help text is part of your API.** Thor auto-generates help from `desc` strings; GLI and Commander generate it from their DSL. Write the help text *before* the implementation — it forces you to design the interface first, and it is what your users will actually read. A CLI with terrible help text is a broken product even if the logic is perfect.

**Zero-dependency claims have a catch.** GLI and Commander advertise no runtime dependencies, but your *tool* still needs the gems installed. If you are building a distributable CLI, prefer gems that ship as executables (Thor via `exe/`), or vendor everything into a single file — see the patterns used by [Go CLI libraries](../2026-06-22-go-cli-libraries-cobra-urfave-cli-bubble-tea-promptui/) where static binaries make distribution trivial by comparison.

**Nesting depth is a design smell.** Just because GLI supports `tool remote add origin` doesn't mean every tool needs three levels. Deep nesting without clear naming conventions produces CLIs that are impossible to discover. If your second level has more than four commands, consider flattening or splitting the tool — our [C++ argument parsing comparison](../2026-06-21-cpp-command-line-argument-parsing-cli11-cxxopts-argparse-docopt/) discusses the same trade-offs from a different language.

**Migrating between frameworks:** the conceptual mapping is `desc`/`def` (Thor) → `command :name do |c|` (Commander) → `desc`/`command` (GLI). Migrations are usually mechanical for flat CLIs; the pain starts with nesting and generators, where Thor's `Thor::Group` has no equivalent in the other two. If you need generators, skip the migration and stay on Thor.

## Performance and Maintenance Considerations

For CLI tools, performance is dominated by Ruby startup time, not the framework — all three add negligible overhead over plain `OptionParser`. What differs is maintenance: Thor benefits from the Rails core team's release cadence and a huge installed base, so security fixes and Ruby-version compatibility land reliably. Commander is stable but smaller; GLI is the quietest — its March 2025 last push means you should test it against each new Ruby release yourself. For team adoption, Thor's ecosystem familiarity wins: any Ruby developer who has run a Rails generator has implicitly used Thor, and the mental model transfers instantly. If you are building a library ecosystem, pairing your CLI with solid testing matters more than the framework choice — the [Ruby testing frameworks comparison](../2026-07-06-ruby-testing-frameworks-rspec-minitest-capybara/) covers how to test CLI behavior properly, and our [Ruby background job guide](../2026-07-28-ruby-background-job-processors-sidekiq-shoryuken-faktory-sucker-punch-comparison/) shows the ecosystem conventions around long-running Ruby processes.

## FAQ

### Is Thor the best Ruby CLI framework in 2026?

For most projects, yes. Thor is used by Rails, Bundler, and Vagrant, is maintained by the Rails core team, and has the richest feature set for generators and file operations. Commander and GLI remain better fits for specific niches: polished user-facing CLIs and deeply nested subcommands respectively.

### What is the difference between Thor and Rake?

Rake is a build tool that executes tasks; Thor is a framework for command-line applications. Thor is Rake-like in syntax but adds command-line option parsing, automatic help, argument validation, and generator support. If your tool takes user input and options, Thor; if it just runs build steps, Rake.

### Does GLI still work with modern Ruby?

GLI is tested against the currently supported Ruby versions per its README, and it has zero runtime dependencies, so it generally keeps working. However, development has slowed since March 2025 — verify compatibility with your Ruby version and budget for self-maintenance.

### Can I use Commander without polluting the global namespace?

Yes. Use the modular style: `require 'commander'` (not `commander/import`) and `include Commander::Methods` inside your own class. This is the recommended approach for libraries and avoids defining `program` and `command` globally.

### Which framework supports deeply nested subcommands?

GLI is purpose-built for git-style nesting with global and per-command options. Thor supports subcommands via the `subcommand` method, but the ergonomics are better in GLI for trees deeper than two levels.

### Should I use a framework at all for a small script?

No. For a throwaway script with a few flags, Ruby's built-in OptionParser is sufficient. Adopt Thor, Commander, or GLI once your tool grows past about five commands or needs automatic help, typed options, or generators — the framework pays for itself quickly at that point.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Ruby CLI Development in 2026: Thor vs Commander vs GLI — Build a Command-Line Tool Users Actually Love",
  "description": "Compare Thor, Commander, and GLI for Ruby command-line development in 2026: subcommand nesting, generators, help generation, dependencies, and migration guidance with real code.",
  "datePublished": "2026-08-12",
  "dateModified": "2026-08-12",
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
