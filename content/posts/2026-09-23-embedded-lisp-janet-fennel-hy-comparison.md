---
title: "Janet vs Fennel vs Hy in 2026: Which Embedded Lisp Should You Actually Use?"
date: "2026-09-23"
tags: ["lisp", "scripting", "developer-tools", "lua", "python"]
cover: "/img/screenshots/janet-lang-lisp.jpg"
draft: false
---

Every serious application eventually grows a scripting layer, and every team that builds one rediscovers the same problem: the configuration language you invented in a weekend is now load-bearing, untested and undocumented. Handing that layer to a real Lisp with a real REPL is one of the highest-leverage refactors available — and in 2026 there are exactly three dialects worth considering for that job.

**Janet** is a standalone bytecode VM with its own runtime. **Fennel** compiles to Lua and inherits the entire Lua ecosystem. **Hy** is Python with parentheses and macros. They solve the same problem — giving your program an embeddable, macro-capable scripting language — with three completely different bets about where the host runtime should come from.

## TL;DR: The Quick Verdict

- **You want an embedded scripting language with no host runtime dependency at all:** pick **Janet**. One C99 build, a bytecode VM, fast startup, and a package manager (`jpm`) that ships with it.
- **Your application already embeds Lua, or you want access to the Lua ecosystem and LuaJIT performance:** pick **Fennel**. It is a single-file compiler, it runs on every Lua from 5.1 to 5.5 plus LuaJIT, and it is the least invasive of the three to adopt.
- **Your application is Python, or your scripts need the Python package ecosystem:** pick **Hy**. It compiles to Python's AST, so it interoperates with every library on PyPI directly — a level of ecosystem access the other two cannot match.
- **If you need none of the above and just want macros in a config file:** you probably want none of these three. A data format with a schema is cheaper than a language with a debugger.

## Feature and Footprint Comparison

All repository data below was pulled live from GitHub on 2026-09-23.

| Dialect | Host runtime | License | Implementation | Package manager | Stars | Last commit |
|---|---|---|---|---|---|---|
| **Janet** | None — self-contained VM | MIT | C99 bytecode VM | `jpm` (bundled) | 4,423 | 2026-09-19 |
| **Fennel** | Lua 5.1–5.5, LuaJIT | MIT | Single-file compiler to Lua | LuaRocks / distro packages | 2,754 | 2026-02-08 |
| **Hy** | CPython 3.x | MIT | Compiles to Python AST | pip / PyPI | 5,438 | 2026-07-31 |

The license column is uniformly friendly — all three are MIT, which is unusual and refreshing for this category. The differences that actually matter are in the first and last columns: **Janet has no host runtime to inherit**, **Fennel borrows Lua's**, and **Hy borrows Python's**. Every other trade-off in this article follows from that single structural choice.

![Hy — a Lisp dialect embedded in Python](/img/screenshots/hy-lisp.jpg)

## Which Dialect for Which Job?

| Use case | Recommended dialect | Why |
|---|---|---|
| Scripting layer inside a C/C++ application | Janet | Embed the VM directly; no Lua or Python requirement imposed on users |
| Plugin system in a game engine already using Lua | Fennel | Zero new runtime — ship the compiler as a single Lua file |
| Automation scripts that call Python libraries | Hy | Direct access to PyPI, including native extension modules |
| Fast startup for short-lived CLI scripts | Janet | Bytecode VM starts faster than interpreter-plus-import-graph |
| Tight numeric loops | Fennel on LuaJIT | LuaJIT's tracing compiler is the fastest runtime of the three |
| Migrating an existing Python codebase incrementally | Hy | Hy and Python modules can import each other, so migration is per-file |
| Air-gapped deployment with no package manager | Fennel | One script or one binary, no dependency resolution at install time |

## Janet: A Lisp That Brings Its Own Runtime

Janet is a dynamic language and bytecode VM written in C99. It has no external dependencies, which is the entire argument for it: you can build Janet into an application and never ask your users to install Lua, Python or anything else.

Building it is deliberately unglamorous. The Makefile requires GNU make, and the standard sequence covers build, test and install:

```sh
cd somewhere/my/projects/janet
make
make test
make repl
make install
make install-spork-git # optional
make install-jpm-git # optional
```

That last pair installs `spork`, the standard utility library, and `jpm`, Janet's package manager and build tool. `jpm` being bundled rather than bolted on matters more than it sounds: it means a Janet project has the same build story whether you are on a laptop or in CI, without a second package manager to audit.

For a statically linked binary — useful for containers and for embedding — the project documents a MUSL build inside Docker, which is the cleanest way to try Janet without touching your host:

```sh
docker run -it --rm alpine /bin/ash
apk add make gcc musl-dev git
git clone https://github.com/janet-lang/janet.git
cd janet
make -j10
make test
make install
```

**Where Janet wins:** embedding. You get one dependency-free runtime, a small core, fibers for cooperative concurrency, and startup fast enough that scripts feel like shell commands. **Where it hurts:** the ecosystem is small and curated. If your scripting layer needs an HTTP client with connection pooling, or a mature test framework, you are probably writing more of it yourself than you would with the other two options.

## Fennel: Lua With Better Syntax and Real Macros

Fennel is a Lisp that compiles to Lua. The distribution model is the clever part: the compiler fits in a single file, `fennel.lua`, and the command-line tool is a single executable script. On Debian and Ubuntu the packaged route is one command:

```bash
sudo apt install fennel
```

If you would rather not depend on distro packaging (versions lag behind releases), download the script, make it executable and drop it on your `$PATH`:

```bash
curl -O https://fennel-lang.org/downloads/fennel-1.6.1
chmod +x fennel-1.6.1
sudo mv fennel-1.6.1 /usr/local/bin/fennel
```

The syntax is regular in a way Lua's is deliberately not — no statements, no operator precedence to memorise, no accidental globals:

```Fennel
(fn fib [n]
  (if (< n 2)
      n
      (+ (fib (- n 1)) (fib (- n 2)))))

(print (fib 10))
```

The embedding story is where Fennel becomes genuinely attractive for applications that already have a Lua VM. Instead of shipping a separate runtime, you drop the compiler into your codebase and load Fennel entry points from Lua:

```lua
require("fennel").install().dofile("main.fnl")
```

That is the whole integration for the flexible case. Compiling ahead of time — producing Lua during your build and shipping only the output — is the alternative when your embedding environment cannot load files from disk. Both paths are documented, and both mean **your plugin authors get macros, destructuring, pattern matching and a real REPL while your runtime remains plain Lua**.

**Where Fennel wins:** adoption cost. No new runtime, no build-system change, and every existing Lua library keeps working — including LuaJIT, which makes Fennel the only one of the three with a tracing compiler under it. Worth reading alongside our [Lua testing frameworks comparison](../2026-09-05-lua-testing-frameworks-busted-luaunit-luassert-comparison/) if you are standing up a test harness for plugin code. **Where it hurts:** you inherit Lua's sharp edges too (1-based indexing, `nil` in the middle of a table, a small integer type on older versions), and the last upstream commit is February 2026, so the project is stable rather than racing ahead.

## Hy: Python, With Macros

Hy is a dialect of Lisp embedded in Python. It does not interpret anything itself: Hy code is compiled into Python's AST, which means it runs on CPython with all the semantics and performance characteristics that implies — including the interpreter's threading constraints.

Installation is a pip install, and the REPL is the entry point:

```bash
pip install hy
hy
```

The reason to choose Hy over the other two is not syntax. It is that inside a Hy program, every Python library is one import away, and Hy modules and Python modules can import each other in both directions. That makes Hy the only one of the three with a credible incremental migration story: you rewrite the file that is causing pain, keep the rest as Python, and nothing breaks at the boundary. Macros operate on that same AST-level representation, which is why Hy macro errors tend to point at something recognisable instead of at a generated intermediate language.

**Where Hy wins:** ecosystem access and migration. If your scripts need to talk to a specific Python client library, or your team already knows Python, Hy removes the "who maintains the embedded runtime" question entirely. **Where it hurts:** you inherit Python's packaging and deployment complexity along with its library access, and scripting layers over Python have a heavy startup cost compared with Janet's VM.

## Pitfalls: The Traps in Embedded Lisp Adoption

**1. You are choosing a runtime, not a syntax.** The three dialects are similar enough in day-to-day code that syntax should not drive the decision. What you are really deciding is whether your users must have Lua installed, must have Python installed, or must have nothing. Embed Janet if the answer to "nothing" matters; embed Fennel if Lua is already there; embed Hy if the application *is* Python.

**2. Stack traces cross a compilation boundary.** Hy and Fennel both compile rather than interpret, so an error surfaces in generated code unless your tooling maps it back. Set up source mapping and a REPL-first workflow before you invite third parties to write plugins, otherwise every bug report arrives as an unreadable trace.

**3. Do not benchmark macros — benchmark startup.** For CLI tools and plugin dispatch, language startup dominates. Janet's VM starts in a fraction of the time a Python import graph needs, which is the real reason Janet feels snappier for short scripts, not the raw throughput of arithmetic.

**4. Version pinning is a security decision.** Fennel's single-file distribution means a user with write access to `$PATH` can replace your compiler. If you embed Fennel, embed a pinned `fennel.lua` in your repository rather than downloading at runtime, and verify release signatures where the project publishes them.

**5. Sandboxing is not free.** All three can call out to the host: Janet through its C library bindings, Fennel through every Lua module it can `require`, Hy through imports. If untrusted users write scripts, define the allowed surface explicitly rather than assuming a Lisp is somehow contained.

**6. Ecosystem gravity is real but asymmetric.** Fennel inherits a mature but small ecosystem. Hy inherits PyPI. Janet inherits almost nothing, which keeps deployments clean and development slower. Decide which failure mode you can live with: a dependency you did not expect, or a library you have to write yourself.

## FAQ

**Which of the three is fastest?**
It depends on the workload rather than on the dialect. Fennel running on LuaJIT has the fastest tight loops because of the tracing compiler. Janet starts fastest, which matters more for short-lived scripts and plugin dispatch. Hy inherits CPython performance exactly — no better, no worse.

**Can I use these dialects for application configuration files?**
You can, and teams do, but think carefully. A configuration file made of Lisp gives users full computation, including the ability to call your internals. If you only need data, a schema-validated format is cheaper to secure. Choose an embedded Lisp when users genuinely need logic, macros or composition.

**Do I need to know Lua to use Fennel?**
Practical Fennel work requires reading Lua. Compilation is transparent, libraries are Lua modules, and error messages come from Lua's runtime. You can learn as you go, but the host language is not optional background reading.

**How does Hy compare with writing plain Python?**
Hy trades tooling familiarity for macro power. You get to write your own control structures and eliminate repetition at compile time; in exchange, your editor, linter and debugger need Hy-aware configuration, and new team members must learn a second syntax. It pays off most in codebases with heavy boilerplate.

**Is Janet suitable as a general-purpose language, or only for embedding?**
Both. It ships a REPL, a package manager and a standard library, so it works for scripts and small services. The distinguishing feature remains embedding: because there is no external runtime, dropping Janet into a C or C++ application does not add an install-time requirement for your users.

**What about other Lisp dialects?**
If you want a full application platform rather than an embedded scripting layer, look at the [Scheme implementations](../2026-09-13-scheme-implementations-racket-chez-guile-comparison/) or the [Common Lisp web stack](../2026-09-11-common-lisp-web-stack-hunchentoot-caveman-clack/). Those are complete environments; the three dialects here are designed to live inside someone else's program.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Janet vs Fennel vs Hy in 2026: Which Embedded Lisp Should You Actually Use?",
  "description": "Janet, Fennel and Hy compared as embedded scripting languages: host runtime, real install and embedding commands, performance characteristics and adoption pitfalls.",
  "datePublished": "2026-09-23",
  "dateModified": "2026-09-23",
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
