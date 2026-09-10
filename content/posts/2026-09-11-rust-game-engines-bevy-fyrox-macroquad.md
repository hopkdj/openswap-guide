---
title: "Bevy vs Fyrox vs macroquad in 2026: Which Rust Game Engine Should You Actually Build With?"
date: "2026-09-11"
tags: ["rust", "game-development", "game-engine", "developer-tools", "gamedev"]
draft: false
---

Rust game development has a reputation problem. The language is fast, the tooling is excellent, and the ecosystem is genuinely healthy — but for years the headline story was a drama about a big engine project collapsing rather than anything anyone actually shipped. That era is over. In 2026 there are three mature, actively developed Rust game engines with real releases, real documentation, and real games, and the question is no longer "is Rust ready for gamedev" but "which of these three fits my project."

The answer is not a matter of taste. **Bevy, Fyrox, and macroquad sit at three genuinely different points on the architecture spectrum**, and picking the wrong one costs you a rewrite — not because the engine is bad, but because the workflow fights how you think about games.

## TL;DR: The Quick Verdict

- **Choose Bevy** if you want the largest ecosystem, the most contributors, and a data-driven Entity Component System that scales from game jam to production. Accept in exchange: breaking changes every ~3 months and a documented "early stages" warning from the maintainers themselves.
- **Choose Fyrox** if you want a **scene editor** as the center of your workflow. Fyrox is the only one of the three that ships a full visual editor, and it is the closest thing Rust has to a Unity-style authoring loop.
- **Choose macroquad** if you are making a 2D game and want to be writing gameplay in ten minutes. It is a library, not a framework: no ECS ceremony, immediate-mode drawing, dependency tree small enough that a clean build takes seconds.

Live project health, September 2026:

| Engine | GitHub stars | Latest release | Downloads (all time) | Last push |
|---|---|---|---|---|
| [Bevy](https://github.com/bevyengine/bevy) | **48,130** | 0.19.1 (2026-08-13) | 7,272,554 | 2026-09-10 |
| [Fyrox](https://github.com/FyroxEngine/Fyrox) | **9,548** | 1.0.1 (2026-03-28) | 72,149 | 2026-09-10 |
| [macroquad](https://github.com/not-fl3/macroquad) | **4,622** | 0.4.16 (2026-07-30) | 1,729,281 | 2026-08-18 |

Notice the shape of that table: Bevy has roughly **5× the stars and 100× the downloads** of Fyrox. Stars are not a quality metric, but download counts on crates.io are a decent proxy for how many people are actually shipping with a library — and Bevy's dominance there is real, not cosmetic.

## Head-to-Head Comparison

| Dimension | Bevy | Fyrox | macroquad |
|---|---|---|---|
| **Architecture** | Data-driven ECS (entities, components, systems) | Scene graph + components | Immediate-mode library (no ECS) |
| **2D vs 3D** | Both, 3D-first | Both, 3D-first | 2D-focused |
| **Visual editor** | No (third-party tools) | **Yes — full scene editor** | No |
| **Release cadence** | Every ~3 months, breaking changes expected | Slower, stabilizing around 1.0 | Frequent, mostly additive |
| **WASM support** | Yes, first-class | Demos runnable in browser | **Yes, single-command deploy** |
| **Best 2D story** | Good | Good | **Excellent** |
| **Learning curve** | Steep (ECS mindset required) | Moderate (editor helps) | **Very shallow** |
| **Renderer** | Modern, wgpu-based | Custom | miniquad (OpenGL/GL ES) |
| **Mobile targets** | Emerging | Emerging | **Android + iOS documented** |
| **Ecosystem depth** | Very large plugin ecosystem | Focused, editor-centric | Small, sharp |

The single most important row is the first one. **ECS architectures ask you to stop thinking in objects and start thinking in data transformations.** If that idea appeals to you, Bevy is the best implementation available in any language. If it makes you tired, macroquad will let you write games the way you always have, and Fyrox will let you do much of the work by clicking instead.

## Decision Matrix: Pick in Ten Seconds

| Your situation | Pick | Why |
|---|---|---|
| First Rust game, 2D, weekend scope | **macroquad** | Working demo in minutes; nothing to learn first |
| Large project, many contributors, long horizon | **Bevy** | 48k stars, massive plugin ecosystem, parallel-by-default systems |
| You want a visual level editor | **Fyrox** | It is the only one of the three with a real scene editor |
| Shipping to Android or iOS | **macroquad** | Documented build paths for both |
| Browser-first release | **Bevy** | First-class WASM with an official example workflow |
| Physics-heavy simulation | **Bevy** | Mature third-party physics plugin integration |
| Team already thinks in ECS | **Bevy** | Do not fight the architecture you already like |
| You hate macro-heavy code | **macroquad** | Plain functions and plain loops |
| You want a stable API you do not have to re-learn | **Fyrox** | 1.0 line is stabilizing; Bevy re-learns quarterly |

## Bevy — The Data-Driven Default

Bevy describes itself as "a refreshingly simple data-driven game engine built in Rust," and its README opens with a warning that deserves to be quoted rather than paraphrased: the engine "is still in the early stages of development. Important features are missing. Documentation is sparse. A new version of Bevy containing breaking changes to the API is released approximately once every 3 months."

That is unusually honest marketing, and it tells you exactly what you are signing up for. Bevy is the most capable engine here **and** the one with the highest maintenance burden between versions. The project publishes migration guides for each release, but the maintainers are candid that "we can't guarantee migrations will always be easy."

What you get in exchange is the cleanest application model of the three. A complete Bevy program that opens a window with standard functionality is genuinely this short — this is the example from the project's own README:

```rust
use bevy::prelude::*;

fn main() {
    App::new()
        .add_plugins(DefaultPlugins)
        .run();
}
```

Everything else is composed on top of that `App`: you add systems, declare components, and let the scheduler parallelize work for you. Adding a dependency is a single line in `Cargo.toml`:

```toml
[dependencies]
bevy = "0.19"
```

The official examples are the real learning resource. Cloning the repository and checking out the release branch is the fastest path to a working game:

```sh
# Switch to the correct version (latest release, default is main development branch)
git checkout latest
# Runs the "breakout" example
cargo run --example breakout
```

Two practical notes that save wasted afternoons. First, **Bevy's minimum supported Rust version tracks close to "the latest stable release"** — the README says so explicitly — so an old toolchain will fail to build and the error will not always point at the toolchain. Run `rustup update` before you file a bug. Second, Bevy's feature flags are the mechanism for controlling compile time and binary size; the repo ships a `docs/cargo_features.md` list precisely because a default `bevy` dependency pulls in far more than most games need.

**Where Bevy is the wrong choice:** if you cannot absorb a breaking API change every quarter, or if your team does not want to learn ECS. Nothing in Bevy is bolted on for people who want a traditional object hierarchy.

## Fyrox — The Editor-First Engine

Fyrox is "a feature-rich, production-ready, general purpose 2D/3D game engine written in Rust with a scene editor." The project was formerly known as **rg3d**, and its 1.0 release line — `fyrox 1.0.1` on crates.io — signals the stability Bevy deliberately does not offer.

The distinguishing feature in one sentence: **Fyrox is the only engine in this comparison with a real visual scene editor.** If your workflow is "place lights, drag meshes, tweak materials in a viewport, then attach scripts," Fyrox is not merely the best Rust option, it is the *only* Rust option. Bevy and macroquad both expect you to author scenes in code or bring your own third-party tooling.

Adding it is conventional Rust:

```toml
[dependencies]
fyrox = "1.0"
```

For project scaffolding there is a companion crate, `fyrox-template`, published on crates.io (30,469 downloads, version 1.0.1). The exact invocation is documented in the project's book rather than its README, so check the current book before scripting a CI setup — this is one of those places where copying a command from a blog post (including this one) is a bad idea.

Fyrox's documentation situation is the inverse of Bevy's. Rather than a scattered set of examples, the project maintains **the Fyrox book at fyrox-book.github.io**, which the README describes as containing "comprehensive information about many aspects of the engine, starting by 'how to build' and ending by various tutorials." That book is the reason Fyrox is approachable despite a smaller community.

For evaluating it without installing anything, the README points at demo projects that **run directly in your web browser** at `fyrox.rs/examples.html`, with source code for each demo in the `FyroxEngine/Fyrox-demo-projects` repository. This is genuinely useful: you can judge the renderer and the editor's output on your own hardware in about two minutes, which is more than most engine comparisons offer.

**The honest trade-off:** a smaller community means fewer Stack Overflow answers, fewer third-party plugins, and a greater chance you are the first person to hit a given issue. In exchange you get a stable 1.0 API, an editor, and a maintainer who ships.

## macroquad — The Minimalist 2D Workhorse

macroquad calls itself "a simple and easy to use game library for Rust," heavily inspired by raylib, and the word *library* is doing important work there. There is no engine to adopt, no ECS to learn, no plugin system to configure. You get a window, a draw call API, and a main loop.

Bevy and Fyrox ask you to buy into an architecture. macroquad asks you to write a `main` function. Here is the complete example from macroquad's README:

```rust
use macroquad::prelude::*;

#[macroquad::main("BasicShapes")]
async fn main() {
    loop {
        clear_background(RED);

        draw_line(40.0, 40.0, 100.0, 200.0, 15.0, BLUE);
        draw_rectangle(screen_width() / 2.0 - 60.0, 100.0, 120.0, 60.0, GREEN);
        draw_circle(screen_width() - 30.0, screen_height() - 30.0, 15.0, YELLOW);

        draw_text("IT WORKS!", 20.0, 20.0, 30.0, DARKGRAY);

        next_frame().await
    }
}
```

Setting up a project is exactly what you would expect from a normal Rust dependency:

```sh
cargo init --bin
```

```toml
[dependencies]
macroquad = "0.4"
```

```sh
cargo run
```

Linux needs a handful of system packages first — paste these from the README rather than guessing, because the exact set differs per distribution:

```sh
# ubuntu system dependencies
apt install pkg-config libx11-dev libxi-dev libgl1-mesa-dev libasound2-dev

# fedora system dependencies
dnf install libX11-devel libXi-devel mesa-libGL-devel alsa-lib-devel

# arch linux system dependencies
pacman -S pkg-config libx11 libxi mesa-libgl alsa-lib
```

Two features make macroquad genuinely special in this comparison.

**First, one command for WASM.** The browser target needs no bundler and no toolchain gymnastics:

```sh
rustup target add wasm32-unknown-unknown
cargo build --target wasm32-unknown-unknown
```

That produces a `.wasm` artifact you load with a small HTML shim and the project's static JS bundle. Serving it locally needs only a static server:

```sh
cargo install basic-http-server
basic-http-server .
```

**Second, a build-time trick that changes how the engine feels.** macroquad's README documents adding this to `Cargo.toml`, which compiles dependencies in release mode even during debug builds:

```toml
[profile.dev.package.'*']
opt-level = 3
```

The README's claim is specific and worth repeating: this makes images load several times faster and applications much more performant "while keeping compile times miraculously low." In practice it means your hot loop runs at real speed while your own code still rebuilds in seconds. It is the single best quality-of-life setting in the Rust 2D ecosystem.

**The async detail that confuses newcomers:** every macroquad game has an `async fn main` with `next_frame().await`. This is not gratuitous. On the web, WebAssembly execution cannot be paused and resumed, so a blocking `loop` would freeze the browser tab. The README explains that macroquad's async support "comes without any external dependencies — no runtime, no executors and futures-rs is not involved." It exists purely to preserve the main function's stack across frames on WASM. If you are coming from a synchronous game loop, this is the one concept worth reading about before you start.

**Where macroquad stops being enough:** large 3D scenes, complex material systems, and anything needing a visual level editor. It is a 2D library with a narrow, sharp scope, and the maintainers are not pretending otherwise.

## Building and Shipping: The Shared Infrastructure Problem

All three engines compile to native binaries and to WebAssembly, and all three have the same CI pain point: **native builds need system graphics and audio libraries that a slim container does not have.** The macroquad package list above is a reliable starting point even for Bevy and Fyrox, because it covers X11, GL, and ALSA.

A Dockerfile that builds any of the three in CI, using the verified Ubuntu package names from macroquad's documentation:

```dockerfile
FROM rust:1-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends \
      pkg-config libx11-dev libxi-dev libgl1-mesa-dev libasound2-dev \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY . .
# Swap the binary name; --release matters enormously for game builds
RUN cargo build --release --bin my_game

# WASM artifact alongside the native one
RUN rustup target add wasm32-unknown-unknown \
    && cargo build --release --target wasm32-unknown-unknown --bin my_game

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
      libgl1 libasound2 libx11-6 libxi6 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /src/target/release/my_game /usr/local/bin/my_game
ENTRYPOINT ["my_game"]
```

Three build-management notes that apply to all three engines:

- **Always build with `--release` for anything you measure.** Debug Rust game builds are one to two orders of magnitude slower in the render loop, and the gap is large enough that people conclude "Rust is slow for games" from a debug build.
- **Keep `target/` out of your container layers.** Cache the Cargo registry and the target directory separately in CI, or every run recompiles the entire dependency graph — which for Bevy means a very long time.
- **Split your build stages.** Native and WASM artifacts have different dependency needs; producing both in one stage keeps image size down and guarantees the two targets are always built from identical source.

For the broader question of building game projects on CI infrastructure — including how to structure build servers for engines like Godot, Bevy, and Defold — our [self-hosted game engine build server guide](../2026-06-07-self-hosted-game-engine-build-servers-godot-bevy-defold-ci-cd-guide/) covers the pipeline side in detail.

## Pitfalls and Migration Notes

**Bevy**

- Pin your version and read the migration guide *before* upgrading. A quarterly breaking release is the documented contract; upgrading without reading is how teams lose a sprint.
- Do not learn Bevy and ECS at the same time as learning Rust. The borrow checker and the scheduler's data access rules interact, and simultaneous learning of both is the most common reason people bounce off.
- Feature flags control everything. Turn off what you do not use before you complain about compile times.

**Fyrox**

- Verify commands against the current book. The engine moved from `rg3d` to `fyrox` naming, and old tutorials on the internet still use the previous crate name and API.
- Smaller community means you will debug more yourself. Budget for that honestly if you are on a deadline.

**macroquad**

- Everything is a library, so you own the architecture. There is no plugin ecosystem to hand problems off to.
- The `async fn main` / `next_frame().await` pattern is mandatory, not optional — plan your state machine around it.
- 2D-only scope is deliberate. If your design has a 3D camera, start with Bevy or Fyrox instead of fighting macroquad's renderer.

**Choosing between them a year from now**

The migration you are most likely to make is macroquad → Bevy, because 2D prototypes grow. That path is relatively gentle: your draw calls become components and systems, and the immediate-mode mental model is a fine foundation for understanding ECS. The migration you are least likely to make successfully is Bevy → macroquad, because you will have built plugin and system structure that has no equivalent. **If you are genuinely unsure, start with macroquad to validate the game idea, then port the parts that survive.**

## FAQ

**Is Rust actually a good language for game development in 2026?**

Yes, with one caveat. Rust's performance and its fearless concurrency are real advantages for simulation-heavy games, and the tooling (Cargo, rustup, cross-compilation) is better than anything in the C++ ecosystem. The caveat is iteration speed: compile times in Rust are slower than in C#, and the borrow checker adds friction during exploratory prototyping. Teams succeed with Rust when they have a clear design; they struggle when they plan to discover the design by iterating in a debugger.

**Which of these three should a beginner pick?**

macroquad, without qualification, for a 2D game. A beginner can be drawing shapes and responding to input in under fifteen minutes, and the immediate-mode API means there is no conceptual framework to learn first. Choose Bevy as a beginner only if you specifically want to learn ECS, and be prepared to spend your first weekend reading rather than building.

**Does Bevy have a visual editor?**

Not an official one. The Bevy project has discussed editor plans for years, and the ecosystem has third-party tooling, but there is no shipped first-party editor comparable to Fyrox's. If a visual authoring loop is a hard requirement, that single fact decides the comparison for you.

**Can I ship any of these to the browser?**

All three, yes. Bevy supports WebAssembly with an official example workflow, macroquad documents single-command WASM deployment and also targets Android and iOS, and Fyrox publishes browser-runnable demos. The practical difference is toolchain friction: macroquad's path is the simplest and Bevy's involves more configuration because there is more engine to initialize.

**How much does the quarterly breaking-change cadence actually cost?**

Less than the warnings suggest, more than the optimists claim. If you pin your dependency and upgrade deliberately once a quarter, the migration guide makes it a scheduled hour of work. The failure mode is transitive: every Bevy plugin in your dependency tree must also have upgraded, so a large plugin-heavy project can be blocked waiting on third parties. Small projects and projects with few plugins pay almost nothing.

**Why is macroquad's download count so much higher than Fyrox's while Fyrox has more than twice the stars?**

Downloads measure how many projects add the dependency — and macroquad, being a small library, is easy to try, is pulled in as a sub-dependency by other 2D projects, and gets included in tutorials. Stars measure how many people want to see a project succeed, which favors ambitious engine projects. Neither number tells you which engine is right for you; treat them as two different signals about two different things.

**Do I need a GPU to develop with these engines?**

You need a working graphics driver to run the games, and you need the system GL and audio development packages to compile them — the package list in this article covers that. For exhaustive benchmark runs, a discrete GPU matters, but all three engines happily run simple 2D scenes on integrated graphics. If you are prototyping in a headless container, plan for a virtual display or do your visual testing on a workstation.

## Related Reading

For the framework layer above the engine layer, our [JavaScript game engine comparison: Phaser vs PixiJS vs Kaboom](../2026-08-18-phaser-vs-pixijs-vs-kaboom-javascript-game-engine-comparison/) is the browser-native counterpart to this article. If your design leans on simulation, the [physics engine comparison: Bullet3 vs Box2D vs Jolt](../2026-06-25-physics-simulation-engines-bullet3-box2d-jolt-physics/) covers integration choices that apply to all three engines here. And because every macroquad game is an async program, the [Rust async runtimes comparison: Tokio vs async-std vs smol](../2026-09-03-rust-async-runtimes-tokio-async-std-smol-comparison/) explains the machinery underneath.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Bevy vs Fyrox vs macroquad in 2026: Which Rust Game Engine Should You Actually Build With?",
  "description": "A practical 2026 comparison of the Bevy, Fyrox and macroquad Rust game engines, covering architecture, editor support, real Cargo and Docker build commands, WASM deployment and migration pitfalls.",
  "datePublished": "2026-09-11",
  "dateModified": "2026-09-11",
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
