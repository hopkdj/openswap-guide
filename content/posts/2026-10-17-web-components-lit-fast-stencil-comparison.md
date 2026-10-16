---
title: "Web Components in 2026: Lit vs FAST vs Stencil — Which Should You Actually Build On?"
date: "2026-10-17"
tags: ["javascript", "frontend", "web-components", "lit", "stencil", "comparison"]
draft: false
cover: "/img/screenshots/lit-logo.jpg"
---

Every frontend team has a rewrite scar. The framework that felt inevitable five years ago is now a maintenance item, and the component library built on top of it is welded to a version that is no longer supported. Web Components are the one part of the browser platform that outlives the framework cycle: `<status-badge>` is a custom element today, in five years, and after the next three framework migrations.

But "use Web Components" is not a plan. The three serious toolchains in 2026 take very different positions: **Lit 3.3** (21,851 GitHub stars, BSD-3-Clause) is a tiny reactive base class for hand-written components, **FAST 3.1** (9,679 stars, MIT) is Microsoft's system for accessible components plus a design-token pipeline, and **Stencil 4.45** (13,143 stars, MIT) is a compiler that emits native custom elements *and* React/Angular/Vue wrappers from one codebase. Choosing badly means either hand-rolling infrastructure you did not want or inheriting a compiler you did not need.

## TL;DR — the 30-second verdict

- **Lit 3.3** — best default for design systems and component libraries you intend to own long-term. Minimal runtime, standard `customElements.define`, no build step required.
- **FAST 3.1** — pick it when accessibility conformance and a design-token/theming pipeline are requirements, not nice-to-haves. Microsoft maintains it and ships a full accessible component set.
- **Stencil 4.45** — pick it when you must ship the same components as native elements *and* as React/Vue/Angular packages to different consuming teams, with docs generated from source.

One line: **Lit for control, FAST for accessibility and theming, Stencil for multi-framework distribution.**

## Side-by-side comparison (npm and GitHub data, October 2026)

| | Lit | FAST | Stencil |
|---|---|---|---|
| GitHub stars | **21,851** | 9,679 | 13,143 |
| Current version | lit **3.3.3** | @microsoft/fast-element **3.1.2** | @stencil/core **4.45.2** |
| License | BSD-3-Clause | MIT | MIT |
| Last repo activity | 2026-09-24 | 2026-10-16 | 2026-10-14 |
| Runtime size (min+gzip) | ~5 KB | ~9 KB | ~6 KB + compiler output |
| Build step required | **No** | No | **Yes (compiler)** |
| Templating | Tagged templates (`html`) | Tagged templates (`html`) | JSX/TSX in `render()` |
| Styling model | `static styles = css` | `css` + design tokens | `styleUrl` / inline + Shadow DOM |
| Server-side rendering | `@lit-labs/ssr` | Not first-class | `dist-hydrate-script` output target |
| Framework wrappers | Manual | Manual | **Auto-generated** (React/Angular/Vue) |
| Form participation | `static formAssociated` | Manual | `formAssociated: true` |
| Prebuilt accessible components | No (primitives only) | **Yes (FAST components)** | No (Ionic ships separately) |
| Docs generation | Manual | Manual | **`stencil build --docs`** |

## Decision matrix — pick in ten seconds

| Your situation | Pick | Why |
|---|---|---|
| You are building a design system for five product teams | **Lit** | Smallest runtime, zero build coupling, easy to publish as plain npm packages |
| You need WCAG-conformant components shipped now | **FAST** | Accessible component set and focus behaviour are maintained by Microsoft |
| Brand theming must be swappable at runtime | **FAST** | Design tokens drive the whole system |
| Consumers are React *and* Vue *and* plain HTML teams | **Stencil** | One codebase, generated wrappers per framework |
| You want components usable as plain ES modules with no bundler | **Lit** | Ships as standard JavaScript modules |
| Documentation and custom-elements metadata must be automatic | **Stencil** | Docs and type metadata are build artefacts |
| You are migrating a legacy design system incrementally | **Lit** | Custom elements can be dropped into an existing page tree |
| You need hydration for a server-rendered storefront | **Stencil** | Hydrate script is a first-class output target |

![Lit — the official project mark from the lit/lit monorepo](/img/screenshots/lit-logo.jpg "Official Lit project logo (lit/lit repository)")

## Lit 3.3 — the smallest thing that works

Lit is a base class plus a template engine, and that is the entire pitch. A component is a class, styles are a tagged template, and rendering is declarative; nothing else is imposed on you. Because it ships as standard ES modules, a component works from a CDN, inside a Vite app, or in a plain static page:

```bash
npm install lit
```

```ts
// status-badge.ts
import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('status-badge')
export class StatusBadge extends LitElement {
  static styles = css`
    .badge { border-radius: 999px; padding: 2px 8px; font: 600 12px/1.6 system-ui; }
    .ok { background: #d1fae5; color: #065f46; }
    .down { background: #fee2e2; color: #991b1b; }
  `;

  @property({ type: String }) status: 'ok' | 'down' = 'ok';

  render() {
    return html`<span class="badge ${this.status}">${this.status}</span>`;
  }
}
```

Three details define the developer experience. **Properties and attributes are not the same thing** — declaring `@property` is what keeps them in sync, and forgetting it is the single most common Lit bug. **Styling is scoped by Shadow DOM**, so you expose a theming surface deliberately with CSS custom properties and `::part`. **Form participation is opt-in** via `static formAssociated = true` plus `ElementInternals`, which is what makes a custom element behave inside a `<form>`.

Lit's weakness is that it is intentionally bare: no component catalogue, no docs generator, no wrappers. You are buying a foundation, not a house. For teams with strong frontend discipline that is a feature; for teams that want batteries included it is a cost.

## FAST 3.1 — accessibility and design tokens as first-class citizens

FAST is two things: `@microsoft/fast-element` (the layer you write components with) and `@microsoft/fast-foundation` (a maintained set of accessible components plus the design-token system behind them). The templating API is a tagged template like Lit's, but the component definition is declared as a single object, which makes the binding between template, styles and element name explicit:

```bash
npm install @microsoft/fast-element @microsoft/fast-foundation
```

```ts
// status-badge.ts
import { FASTElement, customElement, attr, html, css } from '@microsoft/fast-element';

const template = html<StatusBadge>`<span class="badge ${x => x.status}">${x => x.status}</span>`;

const styles = css`
  .badge { border-radius: 999px; padding: 2px 8px; font: 600 12px/1.6 system-ui; }
`.withBehaviors();

@customElement({ name: 'status-badge', template, styles })
export class StatusBadge extends FASTElement {
  @attr status: 'ok' | 'down' = 'ok';
}
```

The real differentiator arrives when you adopt the token pipeline: components consume design tokens, so re-branding a product means swapping a token dictionary rather than editing component CSS. FAST's accessible components handle the tedious parts — focus management, roving tabindex in menus, ARIA wiring in comboboxes — that teams usually get wrong on the first attempt.

The trade-off is ecosystem gravity. FAST has a smaller community than Lit, so third-party examples are rarer, and the design-token tooling is opinionated: adopting it halfway produces a system that is neither token-driven nor plainly styled. Commit to it fully or choose Lit.

## Stencil 4.45 — one codebase, many frameworks

Stencil is not a runtime library; it is a compiler. You write TSX-flavoured components, run a build, and get native custom elements plus optional framework-specific wrappers, documentation and hydration scripts. For organisations where the consuming audience is not one framework, this is the difference between shipping one component library and maintaining four:

```bash
npm init stencil component status-badge
```

```tsx
// src/components/status-badge/status-badge.tsx
import { Component, Prop, h } from '@stencil/core';

@Component({
  tag: 'status-badge',
  styleUrl: 'status-badge.css',
  shadow: true,
  formAssociated: true,
})
export class StatusBadge {
  @Prop() status: 'ok' | 'down' = 'ok';

  render() {
    return <span class={`badge ${this.status}`}>{this.status}</span>;
  }
}
```

The output targets in `stencil.config.ts` are where the leverage lives: `dist-custom-elements` emits tree-shakeable native elements, `dist-hydrate-script` enables server-side rendering with a hydration script, and the React/Angular/Vue output targets generate idiomatic wrapper components so that consumers never touch a custom element directly unless they want to. `stencil build --docs` produces component documentation from your source, which keeps docs honest as the library evolves.

The price is a build system in your critical path. Debugging compiled output is harder than debugging source, the compiler's opinions leak into project structure, and generated wrappers add version coordination work for every consuming team. Stencil earns its keep above roughly five consuming applications; below that, Lit is usually less machinery.

![Stencil — the official project mark from the ionic-team/stencil repository](/img/screenshots/stencil-logo.png "Official Stencil logo (ionic-team/stencil repository)")

## Pitfalls that bite Web Component projects

**Attributes are strings, properties are not.** Writing `<status-badge status="down">` sets a string; `el.status = 'down'` sets a typed value. If your component receives objects or arrays, document property assignment and avoid relying on attribute round-tripping.

**Form controls need `ElementInternals`.** A custom input that does not call `setFormValue` is invisible to `FormData` and to framework form libraries. That one omission breaks checkout flows in ways that are painful to diagnose.

**Cross-boundary events must be composed.** An event dispatched inside Shadow DOM will not escape unless you set `composed: true` (and `bubbles: true`). This is the classic "my framework listener never fires" bug.

**Styling across the shadow boundary is deliberately hard.** Use CSS custom properties for theming, `::part` for surgical overrides, and `adoptedStyleSheets` for shared styles. Do not reach for `:host-context` and hope.

**Server-side rendering needs Declarative Shadow DOM.** Without it, custom elements render as empty tags until JavaScript boots, which wrecks first-contentful-paint on content-heavy pages. Lit provides an SSR package; Stencil provides a hydrate output target; FAST leaves it to you.

**Defining the same element twice throws.** In micro-frontend setups where two bundles import the same component library, the second `customElements.define` call raises a registration error and blanks the component. Share one library instance, or guard registration.

**Testing needs a real browser or a good simulation.** Shadow DOM queries, focus behaviour and form participation do not behave in a jsdom-based test runner the way they do in a browser, so plan for a browser-mode runner in CI.

## Why standards-based components are worth the extra work

The case for Web Components is longevity and reuse, and it is not theoretical. A component built with Lit, FAST or Stencil works in a Vue app, a Rails-rendered page, an Electron shell, and a static marketing site without a compatibility shim, so the same design-system investment serves teams that will never agree on a framework.

The costs are real — you implement more of the primitives yourself, and you think harder about styling and accessibility boundaries. If your entire product is one framework and will stay that way, a framework-native component library is genuinely simpler; see our [React component library comparison of shadcn/ui, Mantine and Chakra](../2026-08-16-shadcn-ui-vs-mantine-vs-chakra-react-component-libraries-comparison/) for that path. If you are choosing between compilation philosophies more broadly, the [Svelte vs Solid vs Qwik reactivity comparison](../2026-08-16-svelte-vs-solid-vs-qwik-fine-grained-reactivity-frameworks-comparison/) covers the same trade-off from a compiler-first angle, and our [JavaScript bundler comparison of esbuild, Rollup, Parcel, SWC and Turbopack](../2026-06-21-javascript-build-bundlers-esbuild-rollup-parcel-swc-turbopack/) is worth reading before you commit Stencil to your build chain.

## FAQ

### Are Web Components production-ready in 2026?

Yes. Custom elements, Shadow DOM and ES modules are supported by every current browser, Declarative Shadow DOM has broad support for server-rendered markup, and `ElementInternals` makes real form participation possible. The remaining rough edges are tooling-related — SSR and testing — and all three toolchains here address them to different degrees.

### Lit or Stencil for a React-heavy organisation?

If React is your only consumer, use a React library. If React is the majority but you also ship components into Vue, Angular or server-rendered pages, Stencil's generated React wrappers give those teams idiomatic props and events without manual glue. Lit can do the same job, but you write and maintain the wrapper layer yourself.

### Does FAST replace Lit?

Not exactly — they overlap heavily as component bases, and the choice usually comes down to whether you want a maintained accessible component set and a token pipeline. Pick FAST when accessibility conformance and runtime theming are explicit project requirements; pick Lit when you want the smallest possible base and full control over styling strategy.

### How large are the bundles really?

The runtime numbers above are only part of the picture: Lit adds about 5 KB gzipped, FAST about 9 KB, and Stencil roughly 6 KB plus its compiled output. Real page weight is dominated by your own component code and shared styles. Defer non-critical components with dynamic `import()` and keep the critical path small.

### Can these components be used alongside an existing framework app?

That is their strongest use case. All three emit standard custom elements, so they can be mounted inside a React, Vue, Angular or server-rendered page and communicate through DOM events and properties. The only recurring integration work is typing the elements in each framework and ensuring events are `composed` and `bubbles` so they cross the shadow boundary.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Web Components in 2026: Lit vs FAST vs Stencil — Which Should You Actually Build On?",
  "description": "Comparison of Lit 3.3, Microsoft FAST 3.1 and Stencil 4.45 for building standards-based Web Component libraries, with real code samples, bundle sizes and integration pitfalls.",
  "datePublished": "2026-10-17",
  "dateModified": "2026-10-17",
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
