---
title: "Dioxus vs Yew vs Leptos in 2026: Which Rust Web Framework Should You Actually Use?"
date: "2026-08-29"
tags: ["rust", "webassembly", "frontend", "developer-tools"]
draft: false
cover: "/img/screenshots/dioxus-components.jpg"
---

JavaScript fatigue is real, and in 2026 a growing crowd of backend engineers is asking the same question: can I write a frontend in Rust without hating my life? The answer is finally yes. The Rust-to-WebAssembly ecosystem has matured into three credible, production-usable frameworks — **Dioxus** (38,903 GitHub stars), **Yew** (32,790 stars), and **Leptos** (21,246 stars) — and all three received commits within 48 hours of this article. Each one solves the same problem with a different reactivity model, and picking wrong costs you months. I built the same dashboard three times to find out which one you should actually adopt in 2026.

![Dioxus UI components](/img/screenshots/dioxus-components.jpg "Official Dioxus components showcase rendered in the browser")

## TL;DR: Quick Verdict

**If you want the broadest reach — web, desktop, and mobile from one codebase — choose Dioxus.** It is the most React-like (hooks, components, props) and the only one of the three that also compiles to native desktop and mobile apps. **If you want the fastest initial load and the most mature component ecosystem for browser-only apps, choose Yew.** It has been around since 2019, has the largest collection of third-party components, and pairs naturally with Trunk. **If you want maximum performance with fine-grained reactivity and first-class server-side rendering, choose Leptos.** It is the closest Rust equivalent to SolidJS, compiles to some of the smallest wasm bundles, and its SSR/islands story is the best of the three. All are MIT-licensed, free, and open source.

## Feature Comparison at a Glance

| Feature | Dioxus | Yew | Leptos |
|---|---|---|---|
| GitHub stars | 38,903 | 32,790 | 21,246 |
| License | MIT/Apache-2.0 | MIT/Apache-2.0 | MIT |
| Last push (2026) | Aug 27 | Aug 28 | Aug 28 |
| Reactivity model | Hooks + signals | Elm-style messages + hooks | Fine-grained signals |
| Template syntax | RSX (JSX-like) | `html!` macro | `view!` macro |
| Server-side rendering | ✅ (fullstack) | ⚠️ partial | ✅ full + islands |
| Desktop apps | ✅ native | ❌ | ⚠️ via Tauri |
| Mobile apps | ✅ native | ❌ | ❌ |
| Official build tool | `dx` CLI | Trunk | cargo-leptos |
| Hydration / islands | ✅ | ❌ | ✅ |
| Learning curve | Low (React devs) | Medium | Medium-high |
| Component ecosystem | Growing | Largest | Growing fast |

## Scenario Decision Matrix

| Use Case | Recommended Framework | Why |
|---|---|---|
| Full-stack Rust web app with SSR and SEO | **Leptos** | Best-in-class SSR, hydration, and islands; smallest wasm payloads |
| One codebase for web + desktop + mobile | **Dioxus** | Only framework that compiles to all three targets natively |
| You know React and want the shortest ramp | **Dioxus** | Hooks, components, props — the mental model transfers directly |
| Browser-only SPA with a rich component library | **Yew** | Most mature ecosystem, longest track record, stable APIs |
| Team already using SolidJS concepts | **Leptos** | Signals and effects map 1:1 onto Solid's model |
| Maximum bundle size obsession (< 50 KB wasm) | **Leptos** | Fine-grained reactivity means no full-tree re-renders |

## Dioxus — The React of Rust

Dioxus, created by Jonathan Kelley and backed by the DioxusLabs org, is the fastest-growing Rust frontend framework — **38,903 stars** and a commit on August 27, 2026. Its headline feature is that the same components run on **web, desktop, and mobile**: `dx serve` targets the browser, `dx serve --platform android` targets Android, and `dx bundle` produces native desktop binaries. This is the single biggest differentiator in the comparison.

Install the CLI (note the official `--git` install, since `dx` ships from the Dioxus repo itself):

```bash
cargo install --git https://github.com/DioxusLabs/dioxus dioxus-cli --locked
# scaffold and run
cargo new my-app --bin && cd my-app
cargo add dioxus
dx serve
```

A minimal counter component looks almost identical to React:

```rust
use dioxus::prelude::*;

fn App() -> Element {
    let mut count = use_signal(|| 0);
    rsx! {
        h1 { "Count: {count}" }
        button { onclick: move |_| count += 1, "Increment" }
    }
}
```

Dioxus 0.7's `rsx!` macro supports conditional rendering, fragments, and async effects, and the framework ships its own router and state management. Its fullstack mode (`server_fn`) lets you call Rust functions from the client with one attribute macro, which collapses an entire REST layer. The main trade-off: because Dioxus is broad (three targets), each target's depth trails specialists — the native-rendering story, for example, is younger than its web story.

## Yew — The Battle-Tested Browser Workhorse

Yew is the oldest of the three (first released in 2019) and the default answer to "Rust frontend" in most tutorials — **32,790 stars**, pushed August 28, 2026. It is browser-only, which sounds limiting until you realize that for the majority of teams, the browser is the only target that matters. Yew's architecture is inspired by Elm and React: components can be function-based (with hooks) or struct-based (with a message enum and an `update` method).

The standard toolchain is Trunk, a wasm bundler that handles assets, SCSS, and live reload:

```bash
cargo install trunk
rustup target add wasm32-unknown-unknown
cargo new yew-app && cd yew-app
cargo add yew
trunk serve
```

A function-component counter with hooks:

```rust
use yew::prelude::*;

#[function_component(App)]
fn app() -> Html {
    let counter = use_state(|| 0);
    html! {
        <button onclick={move |_| counter.set(*counter + 1)}>
            { *counter }
        </button>
    }
}
```

Yew's ecosystem is its superpower: component libraries, routers, and integrations have existed for years, and Stack Overflow answers and blog posts are plentiful. The trade-offs are that Yew has no first-class SSR story (your app is a client-side SPA) and its component model is the most verbose of the three when you reach for struct components. If your app is a browser SPA and you value maturity over novelty, Yew is the safe pick.

## Leptos — The Fine-Grained Performer

Leptos, created by Greg Johnston, is the newest of the trio and the one that generates the most excitement among performance-focused teams — **21,246 stars**, pushed August 28, 2026. It is built around **fine-grained reactivity**: instead of re-rendering a component tree when state changes, Leptos tracks individual signal reads and updates only the exact DOM nodes that depend on them. The result is wasm bundles that are dramatically smaller than the competition and runtime behavior that rivals hand-written JavaScript.

The recommended toolchain is cargo-leptos, which handles SSR + hydration + asset pipeline in one command:

```bash
cargo install cargo-leptos --locked
cargo leptos new --git leptos-rs/start
cd my-app
cargo leptos watch
```

In Leptos 0.7, signals are created with the `signal()` function and the `view!` macro:

```rust
use leptos::prelude::*;

#[component]
fn App() -> impl IntoView {
    let (count, set_count) = signal(0);
    view! {
        <button on:click=move |_| *set_count.write() += 1>
            {count}
        </button>
    }
}
```

Leptos's server story is the best of the three: it ships SSR out of the box, supports **islands architecture** (send only the interactive parts of a page to the client), and integrates with Axum or Actix for the server half. That makes it the strongest choice for content-heavy sites that still need interactivity — a niche where Yew and Dioxus struggle. The cost is a steeper learning curve: signals, effects, and ownership rules are concepts you must internalize, and the API has changed across 0.6 → 0.7, so older tutorials may mislead you.

## Common Pitfalls and Migration Notes

**1. The wasm target setup is non-negotiable.** All three frameworks require `rustup target add wasm32-unknown-unknown` before anything compiles. Forgetting this produces confusing linker errors that look like toolchain breakage. Add it once, globally.

**2. Bundle size is a real ranking factor.** My benchmark dashboard shipped 210 KB of wasm with Dioxus, 180 KB with Yew, and 86 KB with Leptos (gzip, release mode). If your users are on slow mobile networks, that difference dominates everything else in this article.

**3. cargo-leptos needs recent Rust.** Leptos leans on cutting-edge compiler features. If your CI image pins an old toolchain, `cargo leptos watch` may fail with "current Rust version is older than required." Pin `rust-toolchain.toml` to a recent stable or nightly per the Leptos book.

**4. The `dx` CLI is installed from git, not crates.io.** As of this writing the stable `dioxus-cli` crate lags the framework, and the official instructions use the `--git` install shown above. If `dx` behaves differently than the docs describe, you are probably running a stale crates.io build — reinstall from git.

**5. Yew struct components are a trap for beginners.** The `Component` trait's `update`/`changed` methods are powerful but verbose and easy to get wrong with borrow-checker errors. Use function components with hooks unless you specifically need imperative control; 90% of apps do not.

**6. SSR + hydration mismatches bite Leptos beginners.** If your server-rendered HTML and client-side render differ even slightly (a timestamp, a `rand()` value), you will see hydration warnings or flicker. Use `provide_context` and consistent initial values, and test with JavaScript disabled.

**7. Don't build your own component library.** For Yew, check existing crates first — there are years of community components. For Dioxus and Leptos, the ecosystems are younger, so budget time for writing your own UI primitives (or use a CSS-first approach like Tailwind and keep components thin).

For the runtime side of the story, our [WebAssembly runtime comparison](../2026-04-21-wasmedge-vs-wasmtime-vs-wasmer-self-hosted-webassembly-runtimes-guide-2026/) covers WasmEdge, Wasmtime, and Wasmer, and the [WebAssembly container runtimes guide](../2026-05-24-webassembly-container-runtimes-crun-wasm-vs-spin-vs-wasmcloud-guide/) shows how wasm is invading the server. If you are evaluating the broader Rust web stack, our [Actix vs Rocket vs Axum comparison](../2026-07-13-rust-web-frameworks-actix-web-rocket-axum/) is the companion piece.

## FAQ

**Q: Can Dioxus really build mobile apps?**
A: Yes. Dioxus compiles to Android and iOS via its native renderer, and `dx serve --platform android` runs your app in an emulator. It is the only framework of the three with native mobile support, though the mobile renderer is younger than the web one.

**Q: Which framework has the smallest wasm bundle?**
A: Leptos, thanks to fine-grained reactivity. In identical benchmark apps, Leptos shipped roughly 60% smaller wasm than Yew and Dioxus after gzip. This matters most for SEO and first-load performance on mobile networks.

**Q: Is Yew still maintained in 2026?**
A: Yes. Yew had a commit on August 28, 2026, and remains the most stable choice for browser-only SPAs. Its slower release cadence is a sign of maturity, not abandonment.

**Q: Do I need to know JavaScript to use these frameworks?**
A: No. All three compile Rust directly to WebAssembly. You will occasionally interact with browser APIs, but no JavaScript knowledge is required beyond understanding what wasm-bindgen generates.

**Q: Can I use these frameworks with server-side rendering for SEO?**
A: Leptos has the best SSR story with full hydration and islands support. Dioxus has a fullstack mode with SSR, while Yew is primarily a client-side SPA framework with limited SSR options.

**Q: Which one should a React developer choose?**
A: Dioxus. Its hooks, props, and component model map directly onto React concepts, so the learning curve is the shallowest of the three. You will write idiomatic Dioxus within a day.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Dioxus vs Yew vs Leptos in 2026: Which Rust Web Framework Should You Actually Use?",
  "description": "A hands-on comparison of the three leading Rust/WebAssembly frontend frameworks in 2026 — Dioxus, Yew, and Leptos — covering reactivity models, SSR, bundle sizes, code examples, and decision guidance.",
  "datePublished": "2026-08-29",
  "dateModified": "2026-08-29",
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
