---
title: "Floating UI vs Popper vs Tippy in 2026: The Tooltip Migration Guide"
date: "2026-08-25"
tags: ["javascript", "tooltip", "popover", "floating-ui", "frontend"]
draft: false
cover: "/img/screenshots/floating-ui-cover.jpg"
---

Your tooltip stack is on life support and you may not know it yet. Popper.js — the positioning engine behind millions of dropdowns — stopped active development when its maintainer moved the project to Floating UI, and the old `popperjs/popper-core` repository now redirects into the new project entirely. Tippy.js, the most popular tooltip component built on top of Popper, was archived in May 2024. Meanwhile the npm packages still install, the demos still render, and nothing crashes — which is exactly why so many teams are carrying dead dependencies into 2026 without a migration plan. This guide shows you what actually changed, what breaks, and how to move to Floating UI in an afternoon.

## TL;DR — Quick Verdict

If you use **Popper v2**, migrate to **@floating-ui/dom** — the API is a near-drop-in (`createPopper` becomes `computePosition`, modifiers become a middleware array) and the official migration guide covers every edge case. If you use **Tippy.js**, do not wait for a Tippy v7: the project is archived, so move to **Floating UI + your own tooltip logic** (the `@floating-ui/react` interactions handle hover/focus/click for you) or adopt a headless component library that already wraps Floating UI, such as Radix UI. If you are on the ancient **Popper v1 / jQuery** line, treat it as a rewrite, not a migration. Floating UI is the only actively maintained option of the three: 32,706 stars, MIT, and commits as recent as August 2026.

## Quick Comparison

| Dimension | Floating UI | Popper.js v2 | Tippy.js |
|---|---|---|---|
| GitHub stars | **32,706** | 32,706 (repo folded into Floating UI) | 12,254 |
| Status | **Active (push 2026-08-09)** | v2 frozen — successor is Floating UI | **Archived 2024-05** |
| License | MIT | MIT | MIT |
| Positioning API | `computePosition` (async) | `createPopper` (sync) | Uses Popper v2 internally |
| React support | **Official** (`@floating-ui/react`, `react-dom`, `react-native`) | Unofficial wrappers | `@tippyjs/react` (unmaintained) |
| Vue support | Official (`@floating-ui/vue`) | Community | Community |
| Tooltip/popover UI out of the box | No (positioning + interaction hooks) | No (engine only) | **Yes — complete components** |
| Bundle | ~3 KB core | ~6 KB | ~7 KB + Popper |
| Accessibility helpers | `role`, `aria` wiring via interactions | Manual | Basic built-in |

## Decision Matrix — Which One for Your Use Case?

| Use Case | Recommendation | Why |
|---|---|---|
| You already use Popper v2 | **@floating-ui/dom** | Smallest migration — most `modifiers` map 1:1 to middleware |
| You use Tippy and want minimal code change | **@floating-ui/react + custom tooltip component** | Interactions cover hover/focus/click; you write ~30 lines of UI |
| You use Tippy inside React | **Radix UI Tooltip / headless lib** | Already wraps Floating UI, ships accessible, themed tooltips |
| Canvas, WebGL, or non-DOM rendering | **@floating-ui/core + custom platform** | Floating UI's only option that supports custom platforms |
| New project, zero legacy | **@floating-ui/react** (React) or **@floating-ui/dom** | Actively maintained, framework-optional, tiny |

## What Actually Happened to Popper and Tippy

Popper.js v2 (the `@popperjs/core` package) is not "broken" — it is **frozen by design**. The same author who built Popper created Floating UI as its successor, moved the entire project there, and the old `popperjs/popper-core` GitHub repository now resolves to the Floating UI project data. The Floating UI README states it plainly: "Popper is now Floating UI! For Popper v2, visit its dedicated branch and its documentation." In practice this means: the v2 line still works, but there are no new features, no new browser fixes, and no security triage.

Tippy.js is a different story: it was **explicitly archived in May 2024** (repository is read-only). Tippy bundles Popper v2 as its positioning engine, so it inherited the freeze *and* added its own: no more tooltip component updates at all. The npm page still shows healthy weekly downloads because thousands of apps have it pinned in their lockfiles — those downloads are exactly the migration backlog.

The key architectural shift: **Popper v2 positions synchronously, Floating UI positions asynchronously.** `createPopper(reference, popper, options)` returns a Popper instance you can call `.update()` on anytime. Floating UI's `computePosition(reference, floating, options)` returns a Promise, and it re-renders through middleware that can flip, shift, offset, and arrow — the same jobs Popper did via its `modifiers` array.

## Migrating from Popper v2 — Side by Side

Here is the same "tooltip above a button, flipped when it does not fit" built with both engines:

```js
// Popper v2 — @popperjs/core
import { createPopper } from '@popperjs/core';

const button = document.querySelector('#button');
const tooltip = document.querySelector('#tooltip');

const popper = createPopper(button, tooltip, {
  placement: 'top',
  modifiers: [
    { name: 'offset', options: { offset: [0, 8] } },
    { name: 'flip', options: { fallbackPlacements: ['bottom'] } },
  ],
});
```

```js
// Floating UI — @floating-ui/dom
import { computePosition, offset, flip, shift, arrow } from '@floating-ui/dom';

const button = document.querySelector('#button');
const tooltip = document.querySelector('#tooltip');

async function updatePosition() {
  const { x, y, placement } = await computePosition(button, tooltip, {
    placement: 'top',
    middleware: [offset(8), flip(), shift({ padding: 5 })],
  });
  Object.assign(tooltip.style, { left: `${x}px`, top: `${y}px` });
}
updatePosition();
```

The mental model is the same; the wiring differs in four places:

1. **`modifiers: [{name, options}]` → `middleware: [fn, fn]`.** Most Popper modifiers have direct equivalents — `offset`, `flip`, `arrow`, `preventOverflow` (now `shift`), `hide` (now `autoUpdate` covers the reactive part).
2. **Sync instance → async function.** Because middleware can be async, `computePosition` returns a Promise. If you previously called `popper.update()` after DOM changes, call your `updatePosition()` function again — or use `autoUpdate(reference, floating, updatePosition)` which observes resize, scroll, and layout changes for you.
3. **No more `.destroy()`** — remove the floating element and any event listeners you attached; `autoUpdate` returns a cleanup function for exactly this purpose.
4. **Imports changed.** `@popperjs/core` → `@floating-ui/dom` (vanilla), `@floating-ui/react-dom` (positioning-only React), or `@floating-ui/react` (positioning + interactions).

Floating UI publishes an official **migration guide** (floating-ui.com/docs/migration) that maps every Popper modifier and API call to its successor — if your app uses exotic modifiers like `computeStyles` or custom `apply`, that page is the authoritative reference.

## Migrating from Tippy.js — From Component to Composable

Tippy's appeal was that one call gave you a working tooltip:

```js
import tippy from 'tippy.js';
import 'tippy.js/dist/tippy.css';

tippy('#button', {
  content: 'I am a tooltip!',
  placement: 'top',
});
```

There is no Floating UI equivalent of that single call, because Floating UI deliberately ships primitives, not UI. In React, the idiomatic replacement is `useFloating` plus the interactions hooks:

```jsx
import { useFloating, useHover, useFocus, useClick, useRole, useDismiss, useInteractions } from '@floating-ui/react';
import { useState, useRef } from 'react';

function Tooltip({ label, children }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const { x, y, strategy, refs, context } = useFloating({
    open, onOpenChange: setOpen,
    placement: 'top',
  });
  const hover = useHover(context, { move: false });
  const focus = useFocus(context);
  const role = useRole(context, { role: 'tooltip' });
  const dismiss = useDismiss(context);

  const { getReferenceProps, getFloatingProps } = useInteractions([hover, focus, role, dismiss]);

  return (
    <>
      <button ref={refs.setReference} {...getReferenceProps()}>{children}</button>
      {open && (
        <div
          ref={refs.setFloating}
          style={{ position: strategy, top: y ?? 0, left: x ?? 0 }}
          {...getFloatingProps()}
        >
          {label}
        </div>
      )}
    </>
  );
}
```

Yes, that is more code than `tippy('#button', ...)` — that is the point. You now control rendering, theming, animation, and edge cases instead of inheriting Tippy's. The interactions compose: `useHover` + `useFocus` gives you mouse-and-keyboard tooltips, `useRole` wires `role="tooltip"` and `aria-describedby`, and `useDismiss` closes on outside click or Escape. If that still feels like too much ceremony, adopt a headless component library that wraps Floating UI — the [Radix UI Tooltip](https://www.radix-ui.com/primitives/docs/components/tooltip) ships the same positioning with a `<Tooltip.Trigger>/<Tooltip.Content>` API, which is why shadcn-style component libraries work so well with it (we compared those component ecosystems in our [shadcn vs Mantine vs Chakra guide](../2026-08-16-shadcn-ui-vs-mantine-vs-chakra-react-component-libraries-comparison/), and Radix itself in the [headless component comparison](../2026-08-21-radix-primitives-vs-headlessui-vs-ark-ui-headless-component-comparison/)).

## Pitfalls and Migration Gotchas

1. **Async positioning breaks "call update() then measure" code.** Any code that reads `popper.state.rects` synchronously after `update()` must be rewritten around the awaited `computePosition` result — this is the single most common breakage in real migrations.
2. **Tippy pins Popper v2 in its dependency tree.** You cannot upgrade Popper to Floating UI *under* Tippy; the two are unrelated packages. Migrating Tippy means replacing the tooltip component, not swapping a dependency.
3. **`preventOverflow` is not `flip`.** Teams migrating mechanically often map `preventOverflow` to `shift` and forget that `flip` handles placement changes. Read the migration guide's modifier table before cargo-culting your config.
4. **Middlewares are just functions — order matters.** `offset` must come before `flip`/`shift` in the array, or the flip calculation ignores your offset. If a tooltip suddenly hugs its trigger, check middleware order before anything else.
5. **Virtual elements still exist, but the API changed.** Popper's virtual reference (`{ getBoundingClientRect, contextElement }`) becomes `getBoundingClientRect` on a virtual element object in Floating UI — useful for cursor-following tooltips (e.g., a chart crosshair). Our [React select comparison](../2026-08-24-react-select-libraries-react-select-downshift-react-aria-comparison/) shows another place floating-positioning matters in practice: dropdown popovers.
6. **Do not forget `autoUpdate`.** `computePosition` is one-shot. Without `autoUpdate`, tooltips will not track scroll or resize and will drift off their anchors. Tippy and Popper did this for you; Floating UI hands you the lever.
7. **Accessibility is now your job.** Tippy wired `role="tooltip"` and focus handling. With bare Floating UI you must add `useRole`/`useDismiss` (React) or set `role` and `aria-describedby` manually (vanilla) — otherwise keyboard users lose the tooltip entirely.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Floating UI vs Popper vs Tippy in 2026: The Tooltip Migration Guide",
  "description": "Popper v2 is frozen and Tippy.js is archived. Compare Floating UI vs Popper vs Tippy and migrate your tooltips, popovers, and dropdowns with this 2026 guide.",
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

### Is Floating UI a drop-in replacement for Popper.js?

Close, but not literally. The concepts map 1:1 (placement, middleware vs modifiers, offset/flip/shift), and the official migration guide covers every API. The breaking difference is async `computePosition` vs sync `createPopper`, plus `autoUpdate` replacing manual `.update()` calls.

### Why was Tippy.js archived?

The author archived the repository in May 2024. Tippy's positioning depended on Popper v2, whose development had already moved to Floating UI, and the maintainer recommended migrating to Floating UI or headless alternatives rather than continuing a component layer over a frozen engine.

### Is it safe to keep using Popper v2 or Tippy in production?

They still work, but both are now unmaintained: no new browser fixes, no security triage, and the GitHub issues are read-only for Tippy. For a product you will still be shipping in 2027, plan the migration; for a short-lived internal tool, they are acceptable as-is.

### Does Floating UI work with Vue or plain JavaScript?

Yes. `@floating-ui/dom` is vanilla JS, and `@floating-ui/vue` is the official Vue wrapper. React gets `@floating-ui/react` (positioning + interactions) or `@floating-ui/react-dom` (positioning only), plus `@floating-ui/react-native` for React Native.

### What is the bundle-size cost of switching?

Floating UI is smaller than the stack it replaces: roughly 3 KB gzipped for the core, versus ~6 KB for Popper v2 and ~7 KB + Popper for Tippy. Switching usually *shrinks* your bundle.

### Where can I find the official migration documentation?

The migration guide lives at floating-ui.com/docs/migration, and the Popper v2 documentation remains at popper.js.org/docs. The Floating UI README also links the v2 branch directly for reference.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
