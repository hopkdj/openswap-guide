---
title: "Askama vs Maud vs Tera in 2026: Rust HTML Templating, Compile-Time vs Runtime"
cover: "/img/screenshots/maud-cover.jpg"
date: "2026-08-28"
tags: ["rust", "templating", "web-framework", "library-comparison", "rust-libraries"]
draft: false
---

Every Rust web developer eventually hits the same fork in the road: your templates can be checked **at compile time** or at **3 a.m. in production**. Askama compiles Jinja-style templates into type-safe Rust code. Maud turns markup into a macro that is literally part of your binary. Tera, the engine that powers the Zola static site generator, parses templates at runtime and lets you change them without recompiling. All three are excellent; they are excellent at *different things*, and choosing wrong means either fighting the borrow checker for your HTML or shipping a variable-name typo to production. This guide breaks down the choice with live repository data and real code from the official docs.

## TL;DR / Quick Verdict

If you want **maximum safety with familiar Jinja syntax**, choose **Askama** — template errors become compiler errors, and the syntax will feel like home to anyone coming from Django or Flask. If you want **maximum performance and zero indirection**, choose **Maud** — the `html!` macro is the fastest option here and the code stays readable. If you need **runtime-editable templates** — themes, user-customizable emails, hot-reload during development — choose **Tera**; it is the only one of the three that does not force a recompile on every template change. For a typical API-driven web app with a few hand-written pages, Askama is the balanced default.

## Quick Comparison Table

| Criteria | Askama | Maud | Tera |
|---|---|---|---|
| GitHub stars | 1,178 | 2,625 | 4,297 |
| Last push | 2026-08-23 (active) | 2026-05-25 (active) | 2026-08-26 (active) |
| License | MIT/Apache-2.0 | MIT | MIT |
| Syntax | Jinja-style (`.html` files) | Inline macro (`html! {}`) | Jinja2/Django-style (`.tera` files) |
| Checked at | Compile time | Compile time | Runtime |
| Template location | Separate `templates/` dir | Inside Rust code (or `include!`) | Separate dir, loadable at runtime |
| Inheritance / blocks | Yes | Via `PreEscaped` + partials | Yes (first-class) |
| Auto HTML escaping | Yes (opt-out per block) | Yes (opt-out per block) | Yes (default `escape=true`) |
| Macros | Yes | Rust functions | Yes |
| Hot-reload templates | No (recompile) | No (recompile) | **Yes** |
| Works on stable Rust | Yes | Yes | Yes |
| Extra deps at runtime | None (zero runtime cost) | None | Engine (~1 MB) |

## Decision Matrix

| Use Case | Recommended | Why |
|---|---|---|
| Server-rendered pages in Axum/Actix/Rocket | Askama | Jinja syntax + compile-time checking + battle-tested integrations |
| Email templates with user variables | Tera | Keep templates in files, edit without redeploying |
| A tiny binary for an embedded/edge service | Maud | Macro output — no template files, no runtime engine, no fs access |
| Multi-theme or user-customizable output | Tera | Runtime loading means themes are just directories |
| Team coming from Django/Jinja2 | Askama | The syntax was literally modeled on Jinja |
| Existing Zola site that needs Rust integration | Tera | It is Zola's own engine; behavior is identical |
| Maximum rendering throughput | Maud | Compile-time codegen; no parsing at render time |

## Askama — Jinja Syntax, Compile-Time Safety

Askama implements a template rendering engine based on **Jinja** and generates type-safe Rust code from your templates at compile time, driven by a user-defined `struct` that holds the context. At **1,178 stars** with commits on **2026-08-23**, it is actively maintained — and it has an unusual history: it was forked as **Rinja** in 2024 over a docs.rs trademark dispute, and the fork later merged back into Askama. The project also notes it recently switched its own docs from Tera to Rinja, which is a nice vote of confidence in the ecosystem.

The documented quick start is small:

```sh
cargo add askama
```

```jinja
Hello, {{ name }}!
```

```rust
use askama::Template; // bring trait in scope

#[derive(Template)] // this will generate the code...
#[template(path = "hello.html")] // using the template in this path, relative
                                 // to the `templates` dir in the crate root
struct HelloTemplate<'a> { // the name of the struct can be anything
    name: &'a str, // the field name should match the variable name
                   // in your template
}

fn main() {
    let hello = HelloTemplate { name: "world" }; // instantiate your struct
    println!("{}", hello.render().unwrap()); // then render it.
}
```

The feature list is what you would expect from a mature engine: template inheritance, loops, if/else, includes, macros, filters (built-in and custom), whitespace suppression with `-` markers, opt-out HTML escaping, and syntax customization. The key property is that `hello.html` is parsed *during compilation* — a typo in `{{ nmae }}` fails the build, not the request.

## Maud — Markup as a Macro

Maud takes the opposite aesthetic: instead of separate template files, you write markup directly in Rust using the `html!` macro, which compiles to specialized Rust code. It sits at **2,625 stars** with a push on **2026-05-25**. The official getting-started guide is a full program:

```toml
[dependencies]
maud = "*"
```

```rust
use maud::html;

fn main() {
    let name = "Lyra";
    let markup = html! {
        p { "Hi, " (name) "!" }
    };
    println!("{}", markup.into_string());
}
```

That renders `<p>Hi, Lyra!</p>`. Because the template *is* Rust, you get editor autocomplete, refactoring tools, and the borrow checker inside your markup. Conditional logic is ordinary Rust:

```rust
html! {
    @if user.is_admin {
        a href="/admin" { "Admin panel" }
    } @else {
        span { "Welcome, " (user.name) }
    }
}
```

Maud works on stable Rust (the docs recommend nightly for better error messages during development, stable for deploy). There is no runtime engine, no template directory, no filesystem access — for edge/embedded deployments where every byte counts, that is a decisive advantage. The trade-off: dynamic template content controlled by non-developers is not a thing in Maud — your HTML lives in the codebase by design.

## Tera — The Runtime Engine Behind Zola

Tera is a template engine inspired by Jinja2 and the Django template language, and it is the engine that powers the **Zola** static site generator. At **4,297 stars** — the most of the three — with a push on **2026-08-26**, it is extremely active. Its identity is runtime: templates are strings or files parsed when the engine initializes, so you can change them, add themes, or even ship user-editable templates without recompiling your binary.

The template syntax will be familiar to any Jinja2 user:

```jinja2
<title>{% block title %}{% endblock title %}</title>
<ul>
{% for user in users %}
  <li><a href="{{ user.url }}">{{ user.username }}</a></li>
{% endfor %}
</ul>
```

The Rust side follows the same pattern for all three frameworks: create the engine, build a context, render:

```rust
use tera::{Tera, Context};

let tera = Tera::new("templates/**/*.html").unwrap();
let mut context = Context::new();
context.insert("users", &users);
let html = tera.render("users.html", &context).unwrap();
```

Tera supports template inheritance (`{% extends %}` / `{% block %}`), macros, filters, global functions, and per-file auto-escaping (HTML on by default). Because rendering happens at runtime, a typo in a variable name surfaces as a render error instead of a compile error — that is the price of flexibility. For development, `Tera::new` plus re-instantiation gives you hot-reload semantics; in production you typically instantiate once at startup and clone the handle, since `Tera` is cheap to clone and `Send + Sync`.

## Pitfalls and Migration Notes

- **Compile-time engines slow your builds.** Askama and Maud parse/generate code during `cargo build`. On a large crate this is measurable; keep template-heavy code in its own crate or module so incremental rebuilds do not re-render everything.
- **Runtime errors are the hidden cost of Tera.** A missing context key renders an error *at request time*. Mitigate with tests that render every template in your test suite — a `tera.get_template_names()` loop is cheap insurance.
- **Escaping differs by context.** All three auto-escape HTML, but none of them know the difference between HTML, attributes, JavaScript, or CSS contexts. For `onclick="..."` and inline `<script>` interpolation, apply context-specific escaping or pre-escape at the model layer.
- **Askama template paths are relative to `templates/`** — forgetting the directory or misnaming the file produces a compile error (good) that can be confusing (less good). The `#[template(path = "...")]` attribute is checked against the actual filesystem at build time.
- **Maud and whitespace.** Because markup is code, significant whitespace between elements is up to you; `html! { p { "a" } p { "b" } }` will not insert a newline. Use `(PreEscaped("\n"))` or explicit text when the output's formatting matters.
- **Do not render user-controlled template files.** Tera can load templates from arbitrary paths — if a user can influence which file is loaded, that is template injection. Always constrain the template name against a whitelist.
- **`html!` blocks inside `format!`/`write!` strings** are a common source of `{` escaping bugs — the macro owns its braces; keep interpolation inside `(expr)` forms, not string concatenation.
- **Version-pin template engines.** All three are pre-1.0 (0.x) or young; a minor update can change syntax defaults (e.g., whitespace handling). Pin exact versions in `Cargo.toml` for reproducible builds.

For more Rust library comparisons, see our [Rust PDF libraries guide (printpdf, lopdf, pdf-rs)](../2026-08-26-rust-pdf-libraries-printpdf-lopdf-pdf-rs-comparison/), the [general template engine roundup (Jinja2, Handlebars, Mustache, Tera)](../2026-06-21-template-engine-libraries-jinja2-handlebars-mustache-tera/) if you are choosing across languages, and the [self-hosted Rust crate registry guide (Kellnr, Alexandrie, Panamax)](../2026-06-16-self-hosted-rust-crate-registries-kellnr-alexandrie-panamax/) for the rest of the Rust infrastructure story.

## FAQ

### What is the difference between Askama and Tera?

Askama compiles Jinja-style templates to type-safe Rust at **compile time** — template errors fail the build. Tera parses templates at **runtime** — you can edit template files without recompiling, but errors surface at render time.

### Is Maud faster than other Rust template engines?

Generally yes for small templates: the `html!` macro generates direct Rust code with no parsing at render time and no runtime engine. In practice the difference matters most in hot loops; for typical web responses, the framework's serialization and database layers dominate.

### Can I use Tera with Axum or Actix?

Yes. Tera is framework-agnostic; the common pattern is to wrap it in a `Arc<Tera>` and pass it via Axum state or Actix app data. The same applies to Askama, which also has documented integration examples for the major frameworks.

### Does Askama support template inheritance?

Yes — Askama supports template inheritance (`{% extends %}` / `{% block %}`), includes, loops, if/else, macros, and filters, mirroring Jinja. Maud achieves composition through Rust functions and partials; Tera has first-class inheritance like Jinja2.

### Which engine should I pick for a static site generator?

Tera is the engine behind Zola, so it is the natural fit for static site workflows, including themes and content-heavy sites. If you are building a small static output generator inside a Rust application, Maud's compile-time approach also works well with zero runtime dependencies.

### Do these libraries work on stable Rust?

All three work on stable Rust. Maud's docs recommend developing on nightly for better error messages but deploying on stable; Askama explicitly advertises stable Rust support.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Askama vs Maud vs Tera in 2026: Rust HTML Templating, Compile-Time vs Runtime",
  "description": "Compare Askama, Maud, and Tera for Rust HTML templating: compile-time vs runtime rendering, Jinja syntax, macros, performance, and when to pick each engine.",
  "datePublished": "2026-08-28",
  "dateModified": "2026-08-28",
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
