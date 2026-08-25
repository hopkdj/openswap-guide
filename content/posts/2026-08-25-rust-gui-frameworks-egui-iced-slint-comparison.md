---
title: "Rust GUI Frameworks in 2026: egui vs iced vs Slint — Which One Should You Actually Use?"
date: "2026-08-25"
tags: ["rust", "gui", "desktop-apps", "frontend", "cross-platform"]
draft: false
cover: "/img/screenshots/egui-cover.jpg"
---

Rust's tooling story is mature — but its GUI story still forces a fork in the road. You will spend 40 hours wiring up a framework before your first window even looks decent, and picking wrong means ripping out the UI layer of an entire application. The three serious candidates — egui (30,160 stars), iced (31,350 stars), and Slint (23,588 stars) — are not three shades of the same thing. They encode three completely different philosophies about how a UI should work, and the choice quietly decides your team's productivity, your app's feel, and even your licensing options for years.

## TL;DR: Which Rust GUI Framework Should You Pick?

If you need a **tool, dashboard, or internal utility that must look good fast**, choose **egui** — its immediate-mode API renders your entire UI every frame, which makes state handling trivial and iteration absurdly fast. If you need a **polished cross-platform application with rich, animated widgets**, choose **iced** — its Elm-inspired model keeps state and view strictly separated, at the cost of more ceremony and slower compile times. If you need **designer collaboration, multiple languages (Rust, C++, JavaScript, Python), or embedded/device displays**, choose **Slint** — its declarative markup is compiled ahead of time and its live preview closes the designer-developer gap. All three compile to native desktop and web (WASM); none of them is a bad choice — but they optimise for very different jobs.

## Comparison at a Glance

| | egui | iced | Slint |
|---|---|---|---|
| **Stars** | 30,160 | 31,350 | 23,588 |
| **Last push** | 2026-08-25 | 2026-08-16 | 2026-08-25 |
| **License** | Apache-2.0 | MIT | Royalty-free / GPLv3 / Commercial |
| **UI paradigm** | Immediate mode | Retained, Elm architecture | Declarative markup DSL |
| **Rendering** | egui-glow / egui-wgpu | wgpu | wgpu / Skia (soft renderer) |
| **Desktop** | Windows, macOS, Linux, Android | Windows, macOS, Linux | Windows, macOS, Linux |
| **Web (WASM)** | Yes (eframe) | Yes (experimental) | Yes |
| **Embedded** | No | No | Yes (MCU-friendly) |
| **Other language bindings** | No | No | C++, JavaScript, Python |
| **Designer tooling** | None (code-only) | None (code-only) | VS Code live preview, visual editor |
| **Community size** | Very large (used by Rerun, RustDesk ecosystem) | Large | Growing (commercial backing) |

## Decision Matrix: Pick by Use Case

| Use Case | Recommendation | Why |
|---|---|---|
| Internal tool, dashboard, or debugger UI | **egui** | Zero state-sync ceremony; mutate values directly and the UI follows |
| Data-heavy desktop app you'll ship to users | **iced** | Predictable retained-mode widgets, better for long-lived complex screens |
| Embedded display or IoT panel | **Slint** | The only one of the three with a real embedded story (and a GPLv3 path that covers it) |
| Team with designers who need to touch the UI | **Slint** | The .slint markup plus live preview is the closest to a design tool |
| Multi-language team (Rust backend + C++/JS/Python UI) | **Slint** | First-party bindings; egui and iced are Rust-only |
| Fastest possible prototype-to-pixel time | **egui** | One file, one loop, no widget lifecycle to manage |

## egui: The Immediate-Mode Workhorse

egui is pure-Rust, dependency-light, and immediate-mode: instead of building a widget tree that persists, your `ui` closure paints the interface *every frame* from current state. That sounds wasteful, and it is — but it buys something enormous: **the UI can never desync from your data**, because the data is the source of truth by construction. This is why Rerun's visualisation viewer, one of the most impressive Rust apps in the wild, is built on it.

```rust
ui.heading("My egui Application");
ui.horizontal(|ui| {
    ui.label("Your name: ");
    ui.text_edit_singleline(&mut name);
});
ui.add(egui::Slider::new(&mut age, 0..=120).text("age"));
if ui.button("Increment").clicked() {
    age += 1;
}
ui.label(format!("Hello '{name}', age {age}"));
```

To ship it as an app, you wrap it in `eframe`, the official framework that handles windowing, input, and rendering on native and web:

```rust
fn main() -> eframe::Result {
    let options = eframe::NativeOptions::default();
    eframe::run_native(
        "My egui App",
        options,
        Box::new(|_cc| Ok(Box::new(MyApp::default()))),
    )
}
```

One `cargo add eframe` and a single `main.rs` later you have a window. The same codebase targets desktop and browser — egui's web demo (pictured below) runs the full framework in WASM with WebGL.

![egui immediate-mode demo running in the browser](/img/screenshots/egui-inline.jpg "egui's immediate-mode demo, rendered live in a browser via eframe and WebAssembly")

The cost shows up at scale: because everything repaints, complex screens need care (texture caching, `ctx.request_repaint_after()` for low-power idle), and accessibility is still playing catch-up despite the built-in AccessKit support. egui also leans on `ui`-closure plumbing rather than reusable component APIs, so very large teams often hit a ceiling — but for tools, editors, and dashboards it remains the fastest way to ship a great-looking Rust UI. If you are coming from the web world and wondering whether a Rust app even belongs on a user's desktop, our [Electron vs Tauri vs Wails comparison](../2026-08-01-electron-alternatives-tauri-wails-neutralinojs-comparison/) covers the webview alternative path.

## iced: The Elm-Architecture Contender

iced deliberately transplants the Elm architecture into Rust: your app is a pure function of state, messages, and a view. You define a `Message` enum, an `update` function that transitions state, and a `view` function that declares widgets from state. The runtime does the rest — diffing, layout, rendering on wgpu.

```rust
use iced::widget::{button, column, text, Column};

impl Counter {
    pub fn view(&self) -> Column<'_, Message> {
        column![
            button("+").on_press(Message::Increment),
            text(self.value).size(50),
            button("-").on_press(Message::Decrement),
        ]
    }
}

impl Counter {
    pub fn update(&mut self, message: Message) {
        match message {
            Message::Increment => { self.value += 1; }
            Message::Decrement => { self.value -= 1; }
        }
    }
}
```

This discipline is exactly what large applications need: every state transition is explicit and testable, and the widget tree is rebuilt from pure data, so there is no hidden mutable UI state to debug. iced ships a much richer set of built-in widgets than egui — scrollables, pickers, grids, theming — and its retained mode makes complex, animated screens dramatically easier to maintain.

The price is ceremony and compile time. Every screen needs its message type, update arms, and view plumbing, and the crate graph is heavy enough that cold builds are measured in minutes. Web (WASM) support also lags: it works but is labelled experimental, so if the browser is a first-class target for you, egui is the safer bet today. For pure desktop apps, however, iced is the most "product-grade" of the three in terms of feel and widget completeness.

## Slint: The Declarative Markup Approach

Slint is the odd one out — and deliberately so. Instead of writing UI code in Rust, you describe the UI in `.slint`, a small declarative language that compiles to native code. Rust then talks to the UI through typed callbacks and properties.

```slint
export component HelloWorld inherits Window {
    width: 400px;
    height: 400px;

    Text {
       y: parent.width / 2;
       x: parent.x + 200px;
       text: "Hello, world";
       color: blue;
    }
}
```

Because the markup is compiled ahead of time (no interpreter), Slint is fast and small enough to target **embedded systems** — microcontrollers and small displays — something neither egui nor iced can claim. It also ships official bindings for Rust, C++, JavaScript, and Python, so a team can keep a Rust core while exposing the UI to other languages. The VS Code extension and live preview let a designer edit the `.slint` file and see changes instantly, which is the closest any Rust GUI gets to the designer-developer workflow of web tooling.

The catch is licensing, and it is a subtle one. Slint is triple-licensed:

1. **Royalty-free** — free for proprietary desktop, mobile, and web apps, but **explicitly excludes embedded systems**.
2. **GPLv3** — free for open-source projects on every platform, including embedded.
3. **Commercial** — for proprietary embedded deployments (or if you want GPL-free everything).

In practice: open-source app → GPLv3 costs nothing; proprietary desktop app → royalty-free costs nothing; proprietary embedded device → you need the commercial license. Many teams discover that third bullet only after months of development. Read the license file in the repo before you commit — it is unusually clear about the three paths.

## Common Pitfalls and Migration Traps

**"Immediate mode can't scale" is a half-truth.** egui apps with hundreds of widgets work fine if you cache expensive views (`ui.memory()`), avoid rebuilding textures every frame, and use `ctx.request_repaint_after()` when nothing changed. The apps that feel slow are almost always repainting at 60fps while idle — not the framework's fault.

**iced compile times surprise everyone.** The first build of a real iced app can take several minutes even on good hardware; CI pipelines need cache discipline (sccache or cargo's incremental). It's a one-time tax per dependency change, not a per-edit tax, but budget for it.

**Slint's live preview is a trap for layout purists.** The preview is close to, but not identical with, the final render (font metrics differ slightly). Verify text truncation in the compiled app, not only in the preview.

**WebAssembly is not a free checkbox.** All three compile to WASM, but they need different glue: egui uses `eframe` (which brings its own asset pipeline), iced's web support is experimental, and Slint's web path has its own template. If browser deployment is core to your product, prototype that specific target first — see our [WASM runtime comparison](../2026-04-21-wasmedge-vs-wasmtime-vs-wasmer-self-hosted-webassembly-runtimes-guide-2026/) for what runs your compiled module once it's out there.

**Team experience matters more than benchmarks.** A team fluent in React will adapt fastest to Slint's markup; a team of Rust systems programmers will feel at home with egui; a team that loves state machines will thrive with iced. Hire for the framework, or budget two weeks of ramp-up either way.

**Migrating between them is a rewrite, not a refactor.** The three architectures (immediate, retained-Elm, declarative) have zero structural overlap. If you picked wrong, isolate the UI behind a trait boundary early so the pain stays contained — the same advice applies to webview-based shells covered in our [desktop framework guide](../2026-08-10-ghostty-vs-alacritty-vs-wezterm-terminal-emulator-guide/)'s sibling articles on native rendering.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Rust GUI Frameworks in 2026: egui vs iced vs Slint — Which One Should You Actually Use?",
  "description": "Deep comparison of the three leading Rust GUI frameworks: immediate-mode egui, Elm-architecture iced, and declarative-markup Slint. Real GitHub stats, code examples, licensing details, and use-case decision matrix.",
  "datePublished": "2026-08-25",
  "dateModified": "2026-08-25",
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

### Is egui suitable for production desktop applications?

Yes — Rerun's viewer and several commercial tools ship on egui, and the Apache-2.0 license is business-friendly. The main caveats are repaint discipline for battery life and the fact that very large widget trees need caching. For tools, dashboards, and editors it is production-proven.

### Can I build a web app with these Rust GUI frameworks?

All three compile to WebAssembly. egui's eframe web support is the most mature, Slint has a dedicated web template, and iced's web target is still experimental. Treat "runs in the browser" as a per-framework capability to prototype, not a checkbox.

### What is the difference between immediate mode and retained mode?

Immediate mode (egui) redraws the entire UI every frame from current state — simpler logic, no state desync, more repaint work. Retained mode (iced) keeps a persistent widget tree that is diffed and updated — more structure, better for complex animated screens, more ceremony. Slint's declarative markup is a third path: UI described in a DSL, compiled ahead of time.

### Is Slint really free?

Slint is triple-licensed: Royalty-free for proprietary desktop/mobile/web apps, GPLv3 for open-source projects (including embedded), and a commercial license for proprietary embedded use. An open-source project or a proprietary desktop app can use it at no cost; proprietary embedded devices require a commercial license.

### Which framework has the best performance?

For raw frame throughput, egui and iced both render via wgpu/OpenGL and are comparable in practice; egui's immediate mode can waste work if you don't manage repaints. Slint's ahead-of-time compiled markup gives it the smallest footprint, which is why it is the only one of the three that targets microcontrollers.

### How do I choose between egui and iced for a new project?

If your UI is mostly data display, forms, and tool controls, egui gets you there in a fraction of the time. If you're building a long-lived user-facing application with many screens, animations, and strict state requirements, iced's architecture will pay for its extra ceremony.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
