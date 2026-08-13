---
title: "Drag and Drop in 2026: dnd-kit vs react-dnd vs SortableJS — Real Comparison"
date: "2026-08-14"
tags: ["javascript", "react", "drag-and-drop", "frontend", "developer-tools"]
draft: false
cover: "/img/screenshots/sortablejs-demo.jpg"
---

Every modern web app eventually needs drag and drop — a kanban board, a sortable image gallery, a reorderable playlist, a file drop zone — and this is where many teams quietly lose a week. The HTML5 Drag and Drop API that ships in browsers is notoriously inconsistent across platforms: `dragenter`/`dragleave` fire unpredictably, touch devices are ignored, and accessibility is an afterthought. So in 2026 you pick a library. But which one?

The three serious contenders are **dnd-kit** (17,536 stars, the React-native-first modern toolkit), **react-dnd** (21,633 stars, the Redux-inspired veteran), and **SortableJS** (31,165 stars, the framework-agnostic workhorse that powers thousands of admin panels). They look interchangeable at a glance and are completely different under the hood. This guide compares them with real code from their official docs, live repository data, and the failure modes that only show up after you ship.

## TL;DR — Quick Verdict

**Building a new React app? Use dnd-kit** — it is the only one with first-class support for React, Vue, Svelte, Solid, and plain TypeScript, built around a modern, accessible core with keyboard and pointer sensors out of the box. **Need one library that works everywhere — Vue, Angular, jQuery, plain pages — with zero framework commitments? Use SortableJS**; it is the simplest, most battle-tested option for list reordering and has a mature plugin ecosystem. **Choose react-dnd only if you are on an older React codebase and value its declarative item/type/monitor architecture** — otherwise its Redux-style indirection and slower maintenance cadence (last meaningful activity in 2025) make it the weakest pick for new work.

| Dimension | dnd-kit | react-dnd | SortableJS |
|---|---|---|---|
| **Role** | Modern DnD toolkit (framework bindings) | Declarative DnD for React | Vanilla JS list reordering |
| **GitHub stars** | 17,536 | 21,633 | **31,165** |
| **Last push** | 2026-07-13 | 2025-07-06 | 2026-03-24 |
| **License** | MIT | MIT | MIT |
| **Bundle size** | ~20 KB core | ~14 KB + backend | ~40 KB (min) |
| **Framework support** | React, Vue, Svelte, Solid, vanilla | React only | Any framework (vanilla core) |
| **Touch / pointer support** | ✅ Pointer + touch sensors | ❌ needs third-party backend | ✅ built-in |
| **Keyboard / accessibility** | ✅ first-class | ⚠️ manual | ⚠️ partial |
| **Sortable lists** | ✅ via @dnd-kit/dom/sortable | ✅ manual with drop targets | ✅ native, the core feature |
| **Drag between lists** | ✅ | ✅ | ✅ (group) |
| **Cloning / dragging copies** | ✅ | ✅ | ✅ (pull: 'clone') |
| **Best for** | New React/TS apps | Legacy React codebases | Universal list reordering |

| Use Case | Pick | Why |
|---|---|---|
| New React app with sortable lists, grids, kanban | **dnd-kit** | Modern API, accessibility sensors built in, active maintenance |
| Single library across React, Vue, Angular, and plain HTML pages | **SortableJS** | Framework-agnostic core, works anywhere with 3 lines |
| Drag-and-drop upload drop zones | **SortableJS or Uppy** | Native drag events + file handling; see our [file upload comparison](../2026-08-14-javascript-file-upload-libraries-uppy-dropzone-tusd-guide/) |
| Kanban board with multiple columns and card reordering | **dnd-kit (sortable)** | Cross-container sortable is a first-class scenario |
| Legacy React 16/17 codebase, minimal new deps | **react-dnd** | Proven, declarative, stable API for years |
| Dragging between two independent lists with clone behavior | **SortableJS** | `group: {pull: 'clone'}` in one line |

## dnd-kit — The Modern Toolkit

dnd-kit (MIT, **17,536 stars**, last push July 2026) was created to fix what the maintainers saw as fundamental problems in the HTML5 DnD API and in React-specific wrappers: performance under large DOM trees, touch support, and accessibility. In 2026 it ships a rebuilt core — the `@dnd-kit/react` package is now the only required dependency, with the vanilla abstractions installed automatically:

```bash
npm install @dnd-kit/react
```

Making an element draggable is a hook, exactly as documented in the official quickstart:

```jsx
import {useDraggable} from '@dnd-kit/react';

function Draggable() {
  const {ref} = useDraggable({
    id: 'draggable',
  });

  return (
    <button ref={ref}>
      Draggable
    </button>
  );
}
```

Drop targets use the sibling `useDroppable` hook, and a `DragDropProvider` wraps the whole interaction:

```jsx
import {useDroppable} from '@dnd-kit/react';

function Droppable({id, children}) {
  const {ref} = useDroppable({id});

  return (
    <div ref={ref} style={{width: 300, height: 300}}>
      {children}
    </div>
  );
}
```

For sortable lists you add `@dnd-kit/dom/sortable` (or `@dnd-kit/helpers` for the `move` utility) on top of the core. The architecture separates concerns cleanly: **sensors** (pointer, touch, keyboard) detect input, **modifiers** transform drag behavior (constraints like `restrictToVerticalAxis` or `restrictToParentElement`), and **plugins** extend behavior — meaning accessibility isn't a checkbox you bolt on, it's a sensor you enable.

**Where dnd-kit costs you**: it's a React/Vue/Svelte/Solid/TS toolkit, not a magic widget — you compose the interaction yourself (which is the point, but it's more code than SortableJS's one-liner). Its API changed significantly between the legacy `@dnd-kit/core` packages and the new `@dnd-kit/react` surface, so old tutorials can mislead you; use the official migration guide.

## react-dnd — The Declarative Veteran

react-dnd (MIT, **21,633 stars**) has been the standard React drag-and-drop answer since 2014, and its design is unmistakably of that era: it borrows Flux/Redux ideas wholesale. You don't manipulate DOM events; you describe what is dragged with typed **items**, declare compatible **types**, and read state through **monitors**. Install it with its HTML5 backend:

```bash
npm install react-dnd react-dnd-html5-backend
```

Wire the provider once:

```jsx
import { DndProvider } from 'react-dnd'
import { HTML5Backend } from 'react-dnd-html5-backend'

function App() {
  return (
    <DndProvider backend={HTML5Backend}>
      {/* your draggable components */}
    </DndProvider>
  )
}
```

Then each draggable component uses `useDrag` and each target `useDrop`, with a `collect` function that maps monitor state to props — the same pattern the docs have taught for a decade:

```jsx
import { useDrag } from 'react-dnd'

function Card({ id }) {
  const [{ isDragging }, drag] = useDrag(() => ({
    type: 'card',
    item: { id },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  }))

  return <div ref={drag} style={{ opacity: isDragging ? 0.5 : 1 }}>Card {id}</div>
}
```

The declarative item/type/monitor model is genuinely powerful for complex interactions — chess boards, diagram editors, multi-type kanbans — because components stay decoupled and the drag state lives outside the DOM.

**Where react-dnd costs you**: maintenance has slowed (last repository activity mid-2025), touch support requires a third-party backend (`react-dnd-touch-backend`), keyboard accessibility is manual, and the Redux-style indirection is overkill for simple reordering. For new projects in 2026 it's hard to recommend over dnd-kit; for stable legacy apps it remains perfectly solid.

## SortableJS — The Universal Workhorse

SortableJS (MIT, **31,165 stars**) is the most-starred of the three and the simplest to adopt: a single vanilla script that turns any list into a reorderable one. It has official wrappers for Vue, React, Angular, jQuery, Knockout, Ember, and Polymer, but the core itself is framework-free and weighs about 40 KB minified.

```bash
npm install sortablejs --save
```

The entire library, straight from the official demo:

```js
import Sortable from 'sortablejs'

new Sortable(example1, {
    animation: 150,
    ghostClass: 'blue-background-class'
});
```

Drag between two lists by giving them a shared `group`, clone instead of move with `pull: 'clone'`, restrict dragging to a handle, filter out non-draggable items, and control swap thresholds — all via options, no architecture required:

```js
new Sortable(example5, {
    handle: '.handle',  // only drag by the handle element
    animation: 150
});
```

Its plugin ecosystem (MultiDrag, Swap) and the fact that it powers countless production admin panels make it the safest choice when your only requirement is "lists that reorder" in an app that isn't a modern React SPA.

**Where SortableJS costs you**: it's a DOM library, so in React it works around React's virtual DOM (via `react-sortablejs` it manages list mutations directly), which can fight React StrictMode and complex state. For anything beyond lists — arbitrary drag interactions, constraint modifiers, rich accessibility — you're building those behaviors yourself.

## The Hidden Cost: Accessibility and Touch

Here is the metric most comparison tables skip: **can a keyboard-only user complete the drag?** The HTML5 API cannot — and neither can react-dnd's default backend. dnd-kit is the only one of the three where keyboard dragging (arrow keys + space, with live announcements) is a first-class sensor you get by default; SortableJS offers partial keyboard support; react-dnd leaves it to you. If your product is public-facing or enterprise (and accessibility lawsuits are a real 2026 risk), treat dnd-kit's sensor architecture as the tiebreaker. On touch devices the gap is similar: dnd-kit handles pointer events natively, SortableJS has built-in touch support, react-dnd needs a separate backend package.

## Common Pitfalls and Migration Notes

- **SortableJS inside React StrictMode double-renders your list.** The library mutates DOM directly; in React 18/19 strict mode it can reorder items twice or drop state. Prefer `react-sortablejs` with a stable `key`, or move to dnd-kit's controlled `items` + `onSortEnd` model where React owns the state.
- **dnd-kit version confusion is real.** The 2026 `@dnd-kit/react` package replaces the legacy `@dnd-kit/core` + `@dnd-kit/sortable` + `@dnd-kit/utilities` trio. Old StackOverflow answers and tutorials reference the legacy API — check the migration guide before copying code, and pin your versions.
- **`dragenter`/`dragleave` flicker is not your bug.** If you hand-rolled HTML5 DnD and see hover states flashing, it's the platform API firing enter/leave on child elements. Libraries normalize this; if you must stay hand-rolled, track a depth counter in `dragenter`/`dragleave`.
- **Measuring drag position on a zoomed/transformed page.** Coordinate math breaks when CSS `transform` or `zoom` is involved. dnd-kit's `MeasuringStrategy` and modifiers handle this; SortableJS options like `fallbackOnBody` exist precisely for these edge cases — test on an actual transformed container before shipping.
- **Reordering a list of 5,000 rows?** DOM-based reordering (SortableJS) will jank; virtualization plus a state-driven approach (dnd-kit with `move` helper) stays smooth. If you need virtual lists, see the [TanStack Virtual](https://tanstack.com/virtual/latest) integration rather than a bare DOM sortable.
- **Don't build file upload drop zones on raw HTML5 DnD.** Between browser quirks and the need for progress/retry, a purpose-built stack wins. Our [Uppy vs Dropzone vs tusd comparison](../2026-08-14-javascript-file-upload-libraries-uppy-dropzone-tusd-guide/) covers the resumable-upload side end to end.
- **For adjacent frontend library decisions**, see our [JavaScript form libraries comparison (react-hook-form vs Formik vs TanStack Form)](../2026-07-05-javascript-form-libraries-react-hook-form-formik-tanstack-final-form/) and the [JavaScript i18n libraries comparison (i18next vs react-intl vs FormatJS)](../2026-07-28-javascript-i18n-libraries-i18next-react-intl-formatjs-vue-i18n-comparison/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Drag and Drop in 2026: dnd-kit vs react-dnd vs SortableJS — Real Comparison",
  "description": "Hands-on comparison of the three leading drag and drop libraries: dnd-kit, react-dnd, and SortableJS. Real code from official docs, live GitHub stats, accessibility and touch analysis, decision matrix.",
  "datePublished": "2026-08-14",
  "dateModified": "2026-08-14",
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

**Which drag and drop library is fastest in 2026?**
For large lists, dnd-kit wins because it measures collisions outside the React render cycle and supports virtualization; SortableJS is fast for typical lists (a few hundred items) but DOM-based reordering degrades past a few thousand rows. react-dnd is fine for small to medium UIs.

**Does dnd-kit work with Vue or Svelte?**
Yes. The 2026 release explicitly targets React, Vue, Svelte, Solid, and plain TypeScript through separate binding packages. SortableJS also has official wrappers for all major frameworks. react-dnd is React-only.

**Is SortableJS abandoned?**
No — last push was March 2026 and it remains the most-starred library of the three (31,165 stars). Its pace is conservative rather than abandoned: the API is stable and the plugin ecosystem (MultiDrag, Swap) is maintained.

**Why does react-dnd need a separate backend for touch devices?**
react-dnd decouples the drag state machine (dnd-core) from the input source. The default HTML5 backend cannot synthesize touch events, so mobile support requires `react-dnd-touch-backend` or `@react-dnd/touch-backend`. dnd-kit and SortableJS handle touch natively.

**Can I use SortableJS inside a React 19 app?**
Yes, via `react-sortablejs`, but be careful with StrictMode double-invocation and ensure list items have stable keys. If your app is new and heavily state-driven, dnd-kit's controlled model will cause fewer surprises.

**Which library supports dragging between multiple lists?**
All three. dnd-kit: sortable across containers; react-dnd: multiple drop targets with types; SortableJS: shared `group` option — including `pull: 'clone'` for copy-dragging, which is a one-liner unique to SortableJS.

**Is dnd-kit free for commercial use?**
Yes, dnd-kit is MIT licensed, as are react-dnd and SortableJS. None of the three impose licensing fees or attribution requirements beyond the standard MIT notice.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
