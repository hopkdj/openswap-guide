---
title: "CSS-in-JS in 2026: styled-components vs Emotion vs Linaria — Which One Should You Actually Use?"
date: "2026-08-15"
tags: ["css", "react", "javascript", "frontend", "styling"]
draft: false
cover: "/img/screenshots/styled-components-cover.jpg"
---

A single CSS-in-JS mistake costs real money: when Stripe migrated away from runtime CSS-in-JS in 2022, they reported a **~7% end-to-end render speedup** by eliminating the runtime overhead, and when Shopify analyzed their own stack they found React re-renders were triggering style recalculation across entire style sheets — not just the component that changed. Yet at the same time, the developer experience of scoped, typed, dead-code-eliminated styling is so good that CSS-in-JS libraries still power the majority of production React apps. The tension is simple: runtime CSS-in-JS gives you the best DX but taxes your users' CPUs; zero-runtime approaches give performance back but cost you features. In 2026, the three libraries that define this spectrum are styled-components (41,125 stars), Emotion (18,017 stars), and Linaria (12,347 stars) — and the right choice depends almost entirely on one question: **can your team afford the runtime?**

## TL;DR / Quick Verdict

- **Pick styled-components** if you want the most mature, most documented runtime CSS-in-JS with the largest community, first-class React Native support, and you accept the runtime cost for maximum DX.
- **Pick Emotion** if you want the same DX as styled-components but with better performance, a `css` prop, object styles, and predictable composition that avoids specificity wars — it's the pragmatist's choice and the engine behind MUI and Chakra UI.
- **Pick Linaria** if you care about Core Web Vitals, have a non-negotiable performance budget, or are shipping to low-end mobile devices — it compiles your styles to static CSS at build time with zero runtime cost, at the price of losing dynamic theming and React Native support.

## Quick Feature Comparison

| Feature | styled-components | Emotion | Linaria |
|---|---|---|---|
| GitHub stars | **41,125** | 18,017 | 12,347 |
| Last push | 2026-08-11 | 2026-05-06 | 2026-08-10 |
| License | MIT | MIT | MIT |
| Runtime cost | **Yes — style injection on every render** | Yes — but heavily optimized | **Zero — build-time extraction** |
| Primary API | `styled.tagname` + `styled(Component)` | `css` prop + `styled` + object styles | `css` template tag + `styled` |
| Syntax style | Template literals | String AND object styles | Template literals (static extraction) |
| Dynamic props | `props => ...` interpolations | `props => ...` interpolations | `props => ...` (limited, via CSS custom properties) |
| React Native support | **Yes (native)** | Yes (via emotion-native) | No |
| Theming | `ThemeProvider` | `ThemeProvider` | Theme via CSS variables (no runtime provider) |
| SSR | Yes (inlined styles) | Yes (inlined styles) | Yes (static CSS in build) |
| Babel/compiler required | Optional (babel-plugin) | Optional (babel-plugin) | **Required (Babel/Metro/Webpack macro)** |
| Bundle size impact | ~12–15 kB runtime | ~7–11 kB runtime | **0 kB runtime** |
| Built-in source maps & labels | Yes | Yes | Yes |
| Ecosystem | Largest (docs, themes, tools) | MUI, Chakra UI, Gatsby default | Used in React Native Web experiments, perf-focused apps |

## Use Case Decision Matrix

| Use Case | Recommendation | Why |
|---|---|---|
| Large enterprise React app, team velocity matters most | **styled-components** | Best docs, biggest community, every edge case has a StackOverflow answer; RN support keeps one syntax across web + native |
| Design-system / component library (MUI, Chakra-style) | **Emotion** | Object styles serialize to plain JSON (easy to validate and type), predictable composition avoids specificity bugs, smaller runtime |
| Performance-sensitive public site / landing pages | **Linaria** | Zero runtime: your CSS is a static file served with the HTML; no style recalculation on re-render, best Lighthouse scores |
| Next.js app with heavy SSR + streaming | **Emotion or Linaria** | Both handle SSR cleanly; Emotion wins on DX, Linaria on zero-JS cost |
| Mobile-web audience on low-end Android devices | **Linaria** | Runtime style injection is measurable on cheap phones — static CSS removes it entirely |
| Team that wants to keep using SCSS-style nesting and tools | **Linaria** | Your `css` blocks are extracted to plain CSS files you can inspect in DevTools, minified by the CSS pipeline |

## Deep Dive: styled-components — The Category Creator

styled-components, created by Max Stoiber and Glen Maddern in 2016, invented the modern CSS-in-JS API: a template literal that returns a React component with scoped styles attached. Its pitch is "visual primitives for the component age" — styles become components, so they compose, receive props, and are naturally colocated with the markup they style. The README's canonical example is still the fastest way to understand the model:

```tsx
import styled from 'styled-components';

const Button = styled.button<{ $primary?: boolean }>`
  background: ${props => (props.$primary ? 'palevioletred' : 'white')};
  color: ${props => (props.$primary ? 'white' : 'palevioletred')};
  font-size: 1em;
  padding: 0.25em 1em;
  border: 2px solid palevioletred;
  border-radius: 3px;
`;

<Button>Normal</Button>
<Button $primary>Primary</Button>
```

Everything that makes CSS-in-JS addictive is here: props-driven styles, automatic vendor prefixing, scoped class names, dead-code elimination at the module level, and the ability to style *any* component — including third-party ones — with `styled(Component)`. Theming comes from a `<ThemeProvider>` context that makes design tokens available to every styled component, and the library's `babel-plugin-styled-components` adds human-readable class names in development and minified names in production.

The cost is the runtime. styled-components keeps a global style registry and injects `<style>` tags into the document at runtime; every component's interpolated values are evaluated during render, and re-renders can trigger style recalculation. The team has optimized this heavily (the `$` prefix for transient props, `shouldForwardProp`, memoized style computation), but the fundamental model — styles as JavaScript executed in the browser — is what Stripe and Shopify moved away from. If your users are on modern hardware, you may never notice; if they're on 2018-era Android phones, they will.

## Deep Dive: Emotion — The Performance Pragmatist

Emotion describes itself as "the Next Generation of CSS-in-JS," and its README emphasizes exactly the axes where it beats styled-components: **performance with heavy caching in production**, predictable composition, and the flexibility of both string and object styles. It powers MUI (Material UI), Chakra UI, and was Gatsby's default styling solution — a who's-who of performance-sensitive design systems.

The quick start from the official README shows the `css` prop, which is Emotion's signature API — styling an element without creating a new component:

```jsx
/** @jsx jsx */
import { jsx } from '@emotion/react'

let SomeComponent = props => {
  return (
    <div
      css={{
        color: 'hotpink'
      }}
      {...props}
    />
  )
}
```

Because styles are plain objects, they serialize to JSON — which means they can be validated with TypeScript, shared between environments, and composed with spread syntax. Emotion's composition model is deliberately predictable: it generates scoped class names with a fixed ordering scheme so you never fight specificity wars between two components that both want to set `color`. Under the hood it uses the same runtime injection model as styled-components, but with a smaller core (`@emotion/react` + `@emotion/cache` vs styled-components' monolith) and aggressive caching that makes production re-renders cheap.

Emotion also ships `@emotion/styled` for the styled-components API when your team prefers it, plus `@emotion/css` for framework-agnostic use, and `@emotion/native` for React Native. In practice, Emotion is the choice when a team wants styled-components' DX but has measured (or suspects) the runtime cost matters — it's roughly the same model with a leaner engine and better architectural hygiene.

## Deep Dive: Linaria — The Zero-Runtime Rebel

Linaria, from the React Native ecosystem folks at Callstack, answers the runtime problem by removing it entirely. Styles written with Linaria's `css` tag are **extracted at build time** into static CSS files; what ships to the browser is a class name — nothing else. The README demonstrates the model with an example that composes with utility libraries like `polished`:

```jsx
import { modularScale, hiDPI } from 'polished';
import fonts from './fonts';

// Write your styles in `css` tag
const header = css`
  text-transform: uppercase;
  font-family: ${fonts.heading};
  font-size: ${modularScale(2)};

  ${hiDPI(1.5)} {
    font-size: ${modularScale(2.5)};
  }
`;

// Then use it as a class name
<h1 className={header}>Hello world</h1>;
```

Because extraction happens at build time, the resulting CSS is a plain static file: it can be served from a CDN with aggressive caching, minified by the standard CSS pipeline, and inspected in DevTools as ordinary CSS. There is no style injection at runtime, no re-render style recalculation, and no JavaScript dependency — your `<h1>` works even if the React bundle fails to load. Linaria requires a build step (Babel plugin, Webpack loader, or Metro), and its dynamic-prop story is deliberately constrained: runtime-varying styles use CSS custom properties, so interpolation is limited to what CSS variables can express. There's no React Native support — the RN bridge would need a runtime, which defeats the point.

The trade-off is honest: you lose dynamic theming (no `<ThemeProvider>` swapping values at runtime — you switch CSS variables on `:root` instead), and some styled-components patterns (arbitrary JS in interpolations, component-as-selector nesting) don't survive static analysis. For teams with a hard performance budget — Core Web Vitals targets, low-end mobile markets, or simply a "no JS for styling" architectural rule — Linaria is the answer.

For the surrounding CSS toolchain — preprocessors, minifiers, and the build pipeline your extracted styles plug into — see our [PostCSS vs Sass vs Lightning CSS comparison](../2026-08-11-postcss-sass-lightningcss-css-build-pipeline-comparison/). And if you're pairing your styling layer with client-side state, our [Redux vs Zustand vs Jotai vs MobX guide](../2026-07-05-javascript-state-management-redux-zustand-jotai-mobx-pinia/) covers the same DX-versus-runtime trade-offs on the state side.

## Common Pitfalls and Migration Gotchas

**1. The runtime cost is real but not uniform.** styled-components and Emotion both inject styles during render; the cost shows up as style recalculation on re-render and FOUC (flash of unstyled content) if SSR isn't configured. Measure with Lighthouse on a production build before assuming you need zero-runtime — many apps never notice the difference, and Linaria's build-step complexity is its own cost.

**2. SSR misconfiguration causes the "blank flash."** All three libraries SSR correctly, but only when configured: styled-components needs `ServerStyleSheet` and `collectStyles`, Emotion needs `@emotion/server`'s `renderStylesToString`. Skip it and your page flashes unstyled HTML before React hydrates. This is the single most common production bug in styled-components apps.

**3. Interpolation misuse kills performance.** Putting non-style values inside interpolations (`${Math.random()}`-style or large objects) forces the runtime to re-evaluate styles on every render and can blow past memoization. The fix: transient props (`$primary` instead of `primary` — the `$` prefix keeps the prop out of the DOM), `shouldForwardProp`, and keeping interpolations to simple style values.

**4. Specificity wars still exist.** styled-components' generated class names are intentionally low-specificity, which is good — until you mix them with a global CSS reset or utility classes that also target the element. Emotion's predictable composition ordering avoids most of this; Linaria's extracted CSS follows normal cascade rules, so import order matters again.

**5. Migration from styled-components to Emotion is mostly mechanical.** `styled` API is compatible via `@emotion/styled`, so a large app can switch engines incrementally. Migration to Linaria is NOT mechanical: dynamic interpolations must be rewritten as CSS variables, and anything relying on runtime theme context needs a variable-switching strategy first.

**6. `css` prop vs `styled` — don't mix patterns without a convention.** Teams that use both end up with components styled two different ways and a style audit nightmare. Pick one primary API per codebase (Emotion teams usually standardize on `css` prop + object styles; styled-components teams on `styled`).

**7. Bundle-size creep.** Runtime CSS-in-JS adds 7–15 kB gzipped to your JS bundle — trivial on desktop, meaningful on 3G. If your team's Lighthouse budget is tight, run the numbers: Linaria's 0 kB is the only guarantee.

**8. Testing styles is different in zero-runtime mode.** With runtime libraries, Jest snapshots can capture injected CSS; with Linaria the CSS lives in build output, so tests assert on class names — pair it with Playwright or Cypress visual checks instead of relying on snapshot tests.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "CSS-in-JS in 2026: styled-components vs Emotion vs Linaria — Which One Should You Actually Use?",
  "description": "Deep comparison of the three main CSS-in-JS libraries in 2026: styled-components, Emotion, and Linaria. Covers runtime vs zero-runtime costs, DX, theming, SSR, and which to pick per use case.",
  "datePublished": "2026-08-15",
  "dateModified": "2026-08-15",
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

**What is CSS-in-JS and why was it invented?**
CSS-in-JS means writing styles as JavaScript (template literals or objects) inside component files instead of separate `.css` files. It was invented to solve scoping (no more global selector collisions), colocation (styles live next to the markup they style), and dynamic styling (styles that react to props and state) — the three pain points that motivated styled-components in 2016.

**What's the difference between runtime and zero-runtime CSS-in-JS?**
Runtime libraries (styled-components, Emotion) generate and inject `<style>` tags in the browser during render, which costs CPU and adds 7–15 kB to the bundle. Zero-runtime libraries (Linaria) extract styles to static CSS files at build time, so the browser never executes styling code — the CSS is served like any other stylesheet. The trade-off is dynamic capability: runtime libraries can compute styles from any JavaScript, zero-runtime ones are limited to what CSS variables can express.

**Which CSS-in-JS library is the fastest?**
Linaria is the fastest at runtime because it has zero runtime. Among runtime libraries, Emotion is generally faster than styled-components due to its smaller core and caching, though the difference is small on modern hardware. For per-render dynamic styles, all runtime libraries benefit from the same memoization discipline.

**Does CSS-in-JS work with Next.js?**
Yes. styled-components and Emotion both have documented Next.js SSR setups (`ServerStyleSheet` / `@emotion/server`), and Linaria works with Next via its Webpack integration. Next.js 13+ App Router works with all three, though Emotion and styled-components require their SSR helpers for correct streaming output.

**Can I use CSS-in-JS with React Native?**
styled-components supports React Native natively, and Emotion has `@emotion/native`. Linaria does not support React Native — its zero-runtime model is incompatible with RN's runtime style processing. If you need one styling system across web and mobile, styled-components is the default choice.

**Is CSS-in-JS still worth using in 2026?**
Yes — if you choose deliberately. For component libraries and apps where dynamic theming matters, Emotion or styled-components remain excellent. For performance-critical or low-end-device audiences, zero-runtime options like Linaria (or the framework-native alternatives covered in our [CSS frameworks comparison](../2026-08-10-tailwind-vs-unocss-vs-open-props-css-frameworks-guide/)) remove the runtime tax entirely. The "CSS-in-JS is dead" takes from 2022 were about the runtime cost, not the concept — scoped, colocated styles are here to stay.

**Do I need a Babel plugin?**
For styled-components and Emotion, no — the core APIs work without one; plugins add better class names, SSR optimization, and smaller bundles. For Linaria, yes — the build-time extraction requires the Babel plugin or a bundler integration (Webpack/Metro/Vite).

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
