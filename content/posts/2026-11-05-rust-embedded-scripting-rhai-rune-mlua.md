---
title: "Embedded Scripting in Rust in 2026: Rhai vs Rune vs mlua Compared"
date: "2026-11-05"
tags: ["rust", "scripting", "rhai", "lua", "plugin-systems", "developer-tools"]
draft: false
cover: "/img/screenshots/rune-scripting-language-official.jpg"
---

Every nontrivial Rust service eventually grows the same feature request: let someone else supply the logic. Pricing rules, alert thresholds, webhook transforms, workflow steps, game behaviors — the moment a customer asks to change one without a redeploy, you are choosing an embedded scripting engine. Recompiling a plugin as a `cdylib` gives you no sandbox, no resource accounting, and ABI breakage on every toolchain bump; embedding an interpreter gives you all three.

Three engines dominate the Rust ecosystem in 2026, and they are not interchangeable: **Rhai** (5,778 stars) is a purpose-built scripting language that lives entirely in Rust's type system, **Rune** (2,350 stars) is a compiled-to-bytecode dynamic language with first-class async and hot reloading, and **mlua** (2,936 stars) binds real Lua — or Luau, or LuaJIT — into your process. Choosing wrong means either fighting the type system forever or discovering that your "sandbox" can call `os.execute`.

## TL;DR: The Quick Verdict

**For embedding business logic inside a Rust application with tight control over what scripts can touch, use Rhai.** It is pure Rust, dependency-free, has no unsafe surface of its own, and exposes explicit knobs for operation count, expression depth, string size, and array size — which is exactly what a multi-tenant rule engine needs.

**If your scripts are long-lived, hot-reloaded, and benefit from async and real language features (structs, enums, pattern matching, generators), use Rune.** Its unit-compilation model and diagnostics are built for developer-facing tooling.

**If your users already know Lua, or you are embedding into a game/Neovim-adjacent ecosystem, use mlua.** Lua 5.5/5.4/5.3/5.2/5.1, LuaJIT, and Luau through one API, with async bindings and vendored builds.

## The Comparison

| Dimension | Rhai | Rune | mlua |
|---|---|---|---|
| GitHub stars | 5,778 | 2,350 | 2,936 |
| Last push | 2026-11-02 | 2026-10-11 | 2026-11-03 |
| License | Apache-2.0 | Apache-2.0 | MIT |
| Language implemented in | Pure Rust (dependency-free) | Rust | C (Lua) via FFI |
| Execution model | AST walker, optional bytecode VM (`grain`, ~2x) | Compiles to bytecode, stack VM | Lua VM (register-based) |
| Syntax | JS + Rust hybrid | Rust-flavored | Lua |
| `unsafe` in your dependency tree | None | Minimal Rust | Yes (FFI boundary) |
| Async in scripts | No native async | Yes, first-class with generators | Yes, via `mlua` async feature |
| Hot reload | Re-evaluate script | Built-in support | Re-load chunk |
| `no_std` / WASM | Both supported | WASM via wasm32 | WASM via wasm32 (C build) |
| Resource limits | Ops count, depth, string/array/map size | Instruction budget, stack isolation | Memory limit, instruction hook |
| Best fit | Rule engines, config-as-code | Application scripting, plugin SDKs | Lua ecosystem, game modding |

Decision matrix:

| Your situation | Pick | Why |
|---|---|---|
| Pricing/alert rules evaluated thousands of times per second | Rhai | Sub-microsecond warm eval, no FFI, no GC pauses from a foreign heap |
| User-authored plugins that must reload without restart | Rune | Bytecode units, diagnostics, hot-reload support |
| Existing Lua content or team expertise | mlua | Real Lua semantics, not a lookalike |
| Scripts need `await` on host operations | Rune or mlua | Rhai has no async in-language |
| Hard requirement: zero C in the build | Rhai | Pure Rust, no `cc` crate, no system Lua |
| Neovim/WoW/game addon compatibility | mlua (Luau/LuaJIT features) | Only option that runs the real thing |

## Rhai — Rules That Cannot Escape

Rhai is designed around one constraint: no foreign runtime. It is written in Rust, has no required dependencies, and its values are Rust types. That makes it the easiest engine to reason about when the script author is a customer.

```toml
[dependencies]
rhai = { version = "1", features = ["sync"] }
```

```rust
use rhai::{Engine, EvalAltResult, Scope, INT};

fn main() -> Result<(), Box<EvalAltResult>> {
    let engine = Engine::new();

    // Host function the script can call, with full Rust typing.
    let mut engine = engine;
    engine.register_fn("tier_discount", |tier: &str, total: INT| -> INT {
        match tier {
            "gold" => total * 15 / 100,
            "silver" => total * 8 / 100,
            _ => 0,
        }
    });

    let mut scope = Scope::new();
    scope.push("total", 24_900 as INT);
    scope.push("tier", "gold".to_string());

    let script = r#"
        let discount = tier_discount(tier, total);
        if discount > 3000 { 3000 } else { discount }
    "#;

    let discount: INT = engine.eval_with_scope(&mut scope, script)?;
    println!("discount = {discount}"); // 3000, capped
    Ok(())
}
```

The part that matters in production is the limit API. Rhai lets you bound execution without a watchdog thread:

```rust
let mut engine = Engine::new();
engine.set_max_operations(50_000);      // abort after N operations
engine.set_max_expr_depths(32, 16);     // guard against pathological nesting
engine.set_max_string_size(8 * 1024);
engine.set_max_array_size(1_024);
engine.set_max_map_size(256);
engine.set_fast_operators(true);
// engine.set_max_call_levels(...) also available for recursion depth

match engine.eval::<i64>("let x = 0; loop { x += 1; }") {
    Ok(v) => println!("{v}"),
    Err(e) => println!("rejected: {e}"), // exceeds max operations
}
```

Rhai's own benchmarks put one million iterations at about 0.14 s on a single 2.6 GHz core with the AST walker, and enabling the `grain` bytecode feature roughly doubles that throughput. For a rule engine that is comfortably fast — you are usually bound by how often you rebuild the `Engine`, not by evaluation.

![Rhai official banner](/img/screenshots/rhai-scripting-language-official.jpg "Rhai embedded scripting language for Rust, official banner")

Two caveats. Rhai has no async, so any host call that awaits must be resolved before evaluation or exposed as a blocking function. And "pure Rust" does not mean "safe against hostile scripts by default": without `set_max_operations` a script can spin forever, and if you register a host function that touches the filesystem, the script can touch the filesystem. The sandbox is the set of functions you register.

## Rune — A Real Language With a Bytecode Unit

Rune takes the opposite approach: a proper dynamic language, compiled to bytecode, with the compiler exposed as a library so you can surface diagnostics to whoever wrote the script. It supports structs and enums with associated data, pattern matching, template literals, generators, and first-class async — features Rhai deliberately omits.

```toml
[dependencies]
rune = "0.14"
```

```rust
use rune::sync::Arc;
use rune::{Context, Diagnostics, Source, Sources, Vm};

fn main() -> rune::support::Result<()> {
    let context = Context::with_default_modules()?;

    let mut sources = Sources::new();
    sources.insert(Source::memory("pub fn add(a, b) { a + b }")?);

    let mut diagnostics = Diagnostics::new();
    let result = rune::prepare(&mut sources)
        .with_context(&context)
        .with_diagnostics(&mut diagnostics)
        .build_vm();

    if !diagnostics.is_empty() {
        let mut writer = rune::termcolor::StandardStream::stderr(
            rune::termcolor::ColorChoice::Always,
        );
        diagnostics.emit(&mut writer, &sources)?;
    }

    let mut vm = result?;
    let output = vm.call(["add"], (10i64, 20i64))?;
    let value: i64 = rune::from_value(output)?;
    println!("{value}"); // 30
    Ok(())
}
```

Because compilation and execution are separate steps, you can compile once on upload, store the unit, and reuse it across requests — which is what makes Rune viable for hot-reloadable plugins. It also gives you real error messages with source spans, a feature your plugin authors will judge you on.

The trade-offs: the crate is pre-1.0, so minor versions occasionally break API (`Context::with_default_modules`, `prepare`, and `Vm::new` signatures have changed across releases). Its dynamic values are reference-counted and it runs its own garbage-free memory model, which is predictable but means you should benchmark your hot path rather than assume it matches Rhai.

## mlua — Real Lua, With Real Power and Real Risk

`mlua` is a high-level binding to Lua itself, covering 5.1 through 5.5 plus LuaJIT and Luau, with optional vendored compilation so you do not depend on a system `liblua`.

```toml
[dependencies]
mlua = { version = "0.11", features = ["lua55", "vendored", "async", "send"] }
```

```rust
use mlua::prelude::*;

fn main() -> LuaResult<()> {
    let lua = Lua::new();

    // Bound the sandbox before handing it user code.
    lua.set_memory_limit(32 * 1024 * 1024)?;

    let map_table = lua.create_table()?;
    map_table.set(1, "one")?;
    map_table.set("two", 2)?;
    lua.globals().set("map_table", map_table)?;

    lua.load("for k, v in pairs(map_table) do print(k, v) end").exec()?;

    let sum: i64 = lua.load("return 1 + 2").eval()?;
    println!("sum = {sum}");
    Ok(())
}
```

Registering async host functions is where mlua earns its keep — a Lua script can `await` a Rust future without blocking the runtime:

```rust
let fetch = lua.create_async_function(|_lua, url: String| async move {
    // real host work here
    Ok(format!("fetched {url}"))
})?;
lua.globals().set("fetch", fetch)?;
```

The warning label is equally important. Lua ships with a standard library that can read files, start processes, and load C modules; you must strip it (`Lua::new_with(StdLib::TABLE | StdLib::STRING, LuaOptions::default())`) rather than assume it is absent. Lua's C API also means panics must not cross the FFI boundary — mlua converts them, but a misbehaving C module is outside anyone's control. Use `set_memory_limit` plus an instruction-count hook if you accept untrusted scripts.

## Performance and Memory Guidance

| Metric | Rhai | Rune | mlua (Lua 5.5) |
|---|---|---|---|
| 1M loop iterations | ~0.14 s (AST), ~0.08 s (`grain`) | ~0.2–0.4 s | ~0.05–0.1 s |
| Warm call overhead | Sub-microsecond | Low microseconds | Sub-microsecond |
| Memory per instance | Small, Rust-owned | Small, RC-owned | Lua heap + Rust wrapper |
| Compile cost | Parse per eval | Compile once, reuse unit | Parse per load |
| Crash containment | Rust panic = your panic | Rust panic = your panic | FFI boundary; C bugs possible |

The pattern that holds up in production: **parse/compile at the edge, evaluate in the hot path**. Cache `AST` in Rhai (`engine.compile(script)`) and compiled units in Rune; for mlua, keep a `Lua` per worker thread and reload chunks only when the script changes. All three are fast enough that re-parsing per request is usually the real bottleneck, not the language.

## Pitfalls Worth Knowing Before You Commit

- **"Embedded" is not "sandboxed."** Every engine here is safe memory-wise and none is safe by default against a hostile author. Bound operations/instructions, bound memory, and register the smallest possible host API.
- **Rhai's `sync` feature changes your types.** Enabling it makes `Engine` and values `Send + Sync` at a small performance cost — decide early, because it ripples through your abstractions.
- **Rune is pre-1.0.** Pin the exact version and budget for a migration on minor bumps. Its diagnostics API and VM construction have churned repeatedly.
- **mlua's stdlib is a loaded weapon.** `StdLib::ALL` includes `os`, `io`, and package loading. Start from an allowlist.
- **Unbounded recursion is the most common production incident.** Set call-depth limits in Rhai (`set_max_call_levels`) and use Rune's stack isolation; a recursive script should return an error, not abort your worker.
- **Do not put tenant scripts in the same evaluation scope as host state.** Fresh `Scope`/`Context` per request; leaked globals are how one tenant's variable becomes another tenant's input.

If you are building the surrounding plugin infrastructure rather than the language runtime, our [embeddable plugin systems comparison](../2026-06-20-embeddable-plugin-systems-extism-pluggy-abi-stable-libloading/) covers the WASM-based alternative, where the sandbox is a module boundary rather than an interpreter. For the Rust ergonomics around these engines, the [CLI parser comparison](../2026-08-10-rust-cli-parsers-clap-argh-bpaf/) and the [error handling guide](../2026-06-22-rust-error-handling-anyhow-thiserror-eyre-guide/) cover the surrounding patterns you will need.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Embedded Scripting in Rust in 2026: Rhai vs Rune vs mlua Compared",
  "description": "A practical comparison of Rhai, Rune and mlua for embedding a scripting language in Rust applications, with working code, resource-limit configuration, performance guidance and sandboxing pitfalls.",
  "datePublished": "2026-11-05",
  "dateModified": "2026-11-05",
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

### Which Rust scripting engine is fastest?

Lua via mlua is usually fastest on raw loop throughput because the Lua VM is a mature register machine with decades of optimization. Rhai is close for typical rule evaluation and avoids all FFI overhead, especially with the `grain` bytecode feature enabled. Rune is competitive but tends to trail on tight numeric loops. Benchmark your actual workload — the gap is smaller than the difference between caching and not caching compiled scripts.

### Can scripts escape the sandbox and touch the filesystem?

Not through the language itself in any of the three: Rhai and Rune have no file or network APIs unless you register host functions, and mlua only exposes what you include from the Lua standard library. The realistic escape routes are host functions you registered too generously, and — for mlua — a memory bug in a C module. Start from an allowlist and assume every registered function is public API.

### Is Rune stable enough for production?

It is pre-1.0, so treat it as a pinned dependency with a planned migration on each minor version. Its API has changed across releases, but the underlying model (compile a bytecode unit, run it in a VM, reuse it) is sound and the diagnostics are the best of the three. If you cannot tolerate occasional breaking changes, Rhai's 1.x line is the calmer choice.

### How do I stop a script from running forever?

Rhai: `set_max_operations(n)` aborts after a fixed operation count. Rune: run with a constrained budget and isolate stacks; long loops terminate with an error. mlua: set a memory limit and install an instruction-count hook that raises an error after N VM instructions. All three return an error to the host rather than hanging the worker, provided you configure them.

### Do I need to recompile scripts on every request?

No, and you should not. Compile once and cache: `engine.compile(script)` returns an `AST` in Rhai, Rune produces a reusable unit from `rune::prepare(...).build_vm()`, and Lua chunks can be precompiled and loaded repeatedly. Parsing per request typically costs more than evaluation for short scripts.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
