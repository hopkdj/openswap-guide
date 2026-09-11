---
title: "Elm vs PureScript vs ReScript in 2026: Which Type-Safe Frontend Language Actually Ships?"
date: "2026-09-12"
tags: ["elm", "purescript", "rescript", "frontend", "functional-programming", "typescript", "open-source"]
draft: false
cover: "/img/screenshots/elm-online-editor.jpg"
---

## Your TypeScript Build Is Slow and Your Types Are Lying

A function returns `undefined` at runtime despite a return type of `string`. A refactor across 400 files takes nine minutes of CI. A dependency bump silently changes inferred types in three packages you do not own. TypeScript is a massive improvement over untyped JavaScript, but everyone who has shipped a large frontend has hit the same wall: the types are advisory, `any` leaks in from dependencies, and the compiler's speed is bounded by the JavaScript ecosystem it lives in.

Three languages exist specifically to solve that problem — and they take three different bets. **Elm** bets on simplicity and a tiny community. **PureScript** bets on expressive types borrowed from Haskell. **ReScript** bets on zero-cost integration with the JavaScript you already have.

This comparison is based on live repository data pulled in September 2026, plus real install and build commands from each project's official documentation. No invented benchmarks.

## TL;DR: The 30-Second Verdict

- **You want one obvious way to build a web app, and you value a compiler that catches everything** → **Elm**. Best in class for UI correctness, smallest ecosystem, and effectively no runtime exceptions.
- **You want a powerful type system and you are comfortable with Haskell-style abstractions** → **PureScript**. The most expressive of the three; the steepest learning curve.
- **You need to adopt gradually inside an existing JavaScript or React codebase** → **ReScript**. Compiles to readable JavaScript, generates TypeScript types, and is the most actively developed of the three right now.

If your team has never written a functional language, start with Elm or ReScript. PureScript rewards people who already think in type classes and higher-kinded types.

## The Full Comparison

| Dimension | Elm | PureScript | ReScript |
|---|---|---|---|
| Compiler stars | 7,901 | 8,909 | 7,443 |
| Last compiler push | Aug 2026 | Jul 2026 | Sep 2026 |
| Compiles to | JavaScript | JavaScript | JavaScript |
| Type system | Hindley-Milner, no type classes | Row types, type classes, higher-kinded types | Hindley-Milner variant, simpler on purpose |
| Interop with JavaScript | Deliberate and narrow (ports/flags) | FFI per module, explicit | Direct and zero-cost |
| Emits readable JS | Yes | Minified-ish, readable | Human-readable, close to hand-written |
| UI toolkit | `elm/html`, plus `elm-ui` (1,382 stars) | Halogen (1,597 stars) and others | ReScript React bindings |
| Package manager | `elm install` (curated) | Spago (831 stars) | npm / `create-rescript-app` |
| Escape hatches to `any`/untyped | None | None | None |
| Learning curve | Moderate | Steep | Moderate |
| Ecosystem size | Small | Smaller | Growing, npm-compatible |
| Adoption inside existing codebase | All-or-nothing per module boundary | All-or-nothing per module | Gradual, file by file |

![The official Elm Online Editor running the Clock example](/img/screenshots/elm-online-editor.jpg "Elm's official online editor renders and runs code in the browser — the fastest way to evaluate the language")

The most important column is the second-to-last row. **Elm and PureScript are all-or-nothing at the module boundary; ReScript is not.** That single difference decides more real-world migrations than any type-system feature.

## Decision Matrix: Pick in 10 Seconds

| Your situation | Recommended | Why |
|---|---|---|
| Greenfield SPA or dashboard | **Elm** | Compiler forbids runtime exceptions in your code |
| Heavy custom layout and styling | **Elm** + `elm-ui` | Layout as a typed data structure, not CSS strings |
| You need type classes or higher-kinded types | **PureScript** | Elm deliberately omits them |
| Adding types to an existing React app | **ReScript** | Adopt one file at a time, ship the rest unchanged |
| Publishing a library to npm consumers | **ReScript** | Emits readable JS and generates TypeScript definitions |
| Small team, no functional programming experience | **Elm** | One architecture pattern, excellent error messages |
| Node CLI tool with strong types | **PureScript** | Spago bundles a single-file Node app in one command |
| You want the most active compiler | **ReScript** | Latest compiler activity of the three |

## Keep Reading

The JavaScript ecosystem around these languages matters as much as the languages themselves. Our [TypeScript schema validation comparison](../2026-08-12-zod-vs-valibot-vs-yup-typescript-schema-validation-comparison/) covers how to validate data at the boundary, the [JavaScript test runner comparison](../2026-07-21-javascript-testing-frameworks-vitest-jest-playwright/) explains why compile speed changes your test strategy, and the [Rust-based JS bundler comparison](../2026-09-08-rust-js-bundlers-rspack-rolldown-farm-comparison/) shows what a native-speed toolchain does to iteration time.

## Elm — Small Language, Impossibly Few Bugs

Elm's install story is one command, and its toolchain does everything from formatting to packaging:

```sh
npm install -g elm
elm init          # creates elm.json
elm install elm/svg
elm make src/Main.elm --output=main.js
```

The compiler is famously unforgiving, and that is the feature. Every Elm program follows **The Elm Architecture** — model, update, view — so there is exactly one place state changes and one place it renders. Combine that with `elm-ui`, which replaces HTML and CSS with typed layout functions, and you get code where layout errors are unrepresentable. Here is real code from the `elm-ui` README:

```elm
module Main exposing (..)

import Element exposing (Element, el, text, row, alignRight, fill, width, rgb255, spacing, centerY)
import Element.Background as Background
import Element.Font as Font

main =
    Element.layout []
        myRowOfStuff

myRowOfStuff : Element msg
myRowOfStuff =
    row [ width fill, centerY, spacing 30 ]
        [ myElement
        , myElement
        , el [ alignRight ] myElement
        ]

myElement : Element msg
myElement =
    el
        [ Background.color (rgb255 240 0 245)
        , Font.color (rgb255 255 255 255)
        ]
        (text "hello")
```

**The honest downsides:** the compiler receives updates far less frequently than ReScript's; JavaScript interop requires explicit ports, which forces you to define a typed message boundary instead of calling a library inline; and the package registry is curated, so if a library does not exist, you write it. For a small application with a stable scope, that trade is excellent. For a team that needs to pull in fifteen npm packages this quarter, it is painful.

## PureScript — The Most Expressive Type System

PureScript is a small, strictly evaluated language written in and inspired by Haskell. Its selling point is the type system: row types for records, real type classes, higher-kinded types, and a compiler that will not let you through. Setup uses npm plus Spago, the package manager and build tool:

```sh
npm install -g purescript
npm install -g spago
mkdir purescript-pasta && cd purescript-pasta
spago init        # creates spago.yaml, src/Main.purs, test/
spago run         # downloads deps, compiles to output/, runs the app
```

Spago also bundles a project into a single runnable file, which makes it a credible choice for typed Node command-line tools, not just browser code:

```sh
spago bundle --bundle-type app --platform node
node .
```

Because dependencies live in a package set pinned in `spago.yaml`, builds are reproducible in a way npm projects rarely are. Running `spago init` creates a workspace with `spago.yaml`, `src/Main.purs`, and a `test/` directory — a sane default structure with tests wired in from the first commit.

**Where it hurts:** the primary UI library, Halogen, has seen no push since September 2024 while the compiler itself continues to move — a stalled-library risk you must account for. Documentation is spread across the PureScript book, Pursuit, and the Discord. And the abstractions are real: if nobody on your team has used type classes, budget weeks, not days.

## ReScript — Types You Can Actually Adopt

ReScript targets a different problem entirely. It is a robustly typed language that compiles to readable JavaScript, and its adoption story is gradual by design — the README is explicit that you can delete the source files and keep the generated JavaScript if you ever want out.

```sh
npm install rescript        # add the compiler to an existing project
npx create-rescript-app     # or scaffold a new app
npx rescript build -w       # compile in watch mode
```

The React bindings are the reason most people arrive, and the component shape is a decorated function rather than a class:

```rescript
@react.component
let make = (~name: string) => {
  <div> {React.string("Hello, " ++ name)} </div>
}
```

Three properties make ReScript the easiest of the three to justify to a manager. It emits JavaScript close enough to hand-written code that you can diff the output and understand it. It generates TypeScript types for what you export, so TypeScript consumers get full autocomplete without adopting anything. And it uses npm for dependencies, so your existing supply chain, security scanning, and CI configuration keep working unchanged.

**Where it hurts:** the language has been through a rename and syntax migration, so older tutorials reference `bsb` and BuckleScript commands that no longer apply. Community size is smaller than TypeScript's by orders of magnitude, so you will read compiler source occasionally. And the type system is intentionally simpler than PureScript's — if you want higher-kinded types, this is the wrong tool.

## Migration Traps and Pitfalls

1. **Treat the interop boundary as the architecture, not an afterthought.** Elm's ports and PureScript's FFI are where bugs will live, because they are the only untyped seams left. Write a thin, tested wrapper per external library.
2. **Do not migrate a whole codebase at once.** ReScript supports file-by-file adoption for a reason. Pick one leaf feature, convert it, measure build time and bundle size, then decide.
3. **Budget for tooling, not just syntax.** Editor support, linting, and CI caching differ sharply across the three. ReScript ships a built-in pretty printer and editor plugins; Elm's toolchain is complete but narrow; PureScript expects you to assemble more of the pipeline yourself.
4. **Check library liveness before you commit.** Halogen's last push in September 2024 versus an active compiler is exactly the pattern that strands a project midway through a migration.
5. **Ignore star counts as a proxy for ecosystem health.** These three compilers are within 1,500 stars of each other, yet their usable library ecosystems differ by a much wider margin. Inspect the libraries you actually need.
6. **Keep a one-file escape hatch.** Every team eventually needs to call something exotic. Decide in advance whether that means a port, an FFI module, or a `%raw`-style escape — and document it.

## FAQ

**Is Elm still maintained in 2026?**
Yes. The compiler received pushes as recently as August 2026 and the `elm-ui` layout library is actively updated. Development is slower and more conservative than ReScript's, and the language design is deliberately frozen to avoid churn, which is a feature for long-lived projects.

**Can I use ReScript in an existing React codebase without rewriting it?**
Yes, and this is its strongest selling point. You add the compiler as an npm dependency, convert one component at a time, and both languages coexist because ReScript compiles to plain JavaScript modules. The generated output is readable enough to review in a pull request.

**Why does PureScript need a package manager separate from npm for dependencies?**
Spago uses a curated package set pinned in `spago.yaml`, so every dependency version is known to be compatible with the others. That is why `spago run` produces reproducible builds, and why you install the compiler itself with npm but resolve library dependencies through Spago.

**Which of the three has the smallest runtime overhead?**
All three compile to JavaScript and add no runtime framework of their own. Elm and ReScript produce especially small bundles because the compilers aggressively eliminate unused code. PureScript output is comparable, though its generated code is less human-readable.

**Do any of these replace TypeScript for backend work?**
Only indirectly. ReScript works well for Node services and can generate TypeScript definitions for consumers. PureScript can bundle a single-file Node application with `spago bundle`, making it viable for command-line tooling. Elm is browser-focused.

**How long does it take a TypeScript developer to become productive?**
ReScript is measured in days because the syntax and npm workflow feel familiar. Elm takes a week or two, mostly to unlearn imperative state management. PureScript takes considerably longer if you have never worked with type classes.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Elm vs PureScript vs ReScript in 2026: Which Type-Safe Frontend Language Actually Ships?",
  "description": "A 2026 comparison of Elm, PureScript, and ReScript for type-safe frontend development, covering type systems, JavaScript interop, install and build commands, adoption strategy, and migration pitfalls.",
  "datePublished": "2026-09-12",
  "dateModified": "2026-09-12",
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
