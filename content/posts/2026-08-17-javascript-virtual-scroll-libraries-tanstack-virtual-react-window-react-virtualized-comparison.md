---
title: "JavaScript Virtual Scrolling in 2026: TanStack Virtual vs react-window vs react-virtualized"
date: "2026-08-17"
tags: ["javascript", "react", "frontend", "performance"]
draft: false
cover: "/img/screenshots/tanstack-virtual-cover.jpg"
---

Your analytics dashboard needs to render a table with 50,000 rows. Naively mapping that array to DOM nodes produces tens of megabytes of markup, a multi-second initial paint, and scroll jank that makes the page feel broken. The fix — rendering only the rows actually visible in the viewport plus a small overscan buffer — is called windowing or virtual scrolling, and every serious frontend eventually needs it. In 2026 the choice comes down to three libraries: **TanStack Virtual (7,067 stars), react-window (17,202 stars), and react-virtualized (27,080 stars)** — and the surprising part is that the most-starred one is the one you should probably stop adopting today.

## TL;DR / Quick Verdict

Use **TanStack Virtual** for new projects: it is headless, framework-agnostic (React, Solid, Vue, Svelte, vanilla), and lets you keep full control of markup and styles while handling fixed, dynamic, and measured sizes. Use **react-window** if you want a small, React-only component library and you are comfortable with its v2 API — it powers React DevTools and stays tiny. **Avoid react-virtualized for new work**: it has been in maintenance mode since early 2025, its API is class-component era, and its maintainer wrote react-window specifically to replace it.

## Feature Comparison (live GitHub data, August 2026)

| Feature | TanStack Virtual | react-window | react-virtualized |
|---|---|---|---|
| GitHub stars | 7,067 | 17,202 | 27,080 |
| Last push | 2026-08-09 | 2026-07-20 | 2025-01-20 |
| Latest version | v3 (2026) | 2.3.0 | 9.22.x |
| Framework support | React, Solid, Vue, Svelte, vanilla | React only | React only (class components) |
| Architecture | Headless hook/function | Component-based (v2 `List`) | Component-based |
| Bundle size | ~10–15 kB | Tiny | Large |
| Dynamic row heights | Yes (measured) | Yes (`useDynamicRowHeight`, less efficient) | Yes (`CellMeasurer`) |
| Sticky items | Yes | No | No |
| Grid (row + column) virtualization | Yes | Yes | Yes |
| Window-scroll virtualization | Yes (built-in utilities) | No | No |
| Maintenance status | Active | Active | Maintenance mode |
| TypeScript | First-class | Included | Included |

## Use-Case Decision Matrix

| Use Case | Recommendation | Why |
|---|---|---|
| New React dashboard with 10K+ rows | **TanStack Virtual** | Headless = your markup, your styles; dynamic measurement built in; active development |
| Multi-framework team (Vue + React + Svelte) | **TanStack Virtual** | One library across frameworks with the same `useVirtualizer` mental model |
| Small, stable React app that just needs a list | **react-window** | Minimal API surface, tiny bundle, proven in React DevTools and Replay |
| Legacy app already on react-virtualized | **react-virtualized** | Don't rewrite what works; plan a migration when you touch the list code |
| Server-rendered or embeddable lists | **react-window** | `defaultHeight` prop exists specifically for SSR initial render |
| Data grids with sticky headers | **TanStack Virtual** | Sticky item support pairs with [TanStack Table](../2026-08-12-tanstack-table-vs-ag-grid-vs-gridjs-javascript-data-grid-comparison/) for full-featured grids |

## TanStack Virtual — Headless Windowing Done Right

TanStack Virtual takes the same philosophy as the rest of the TanStack family (Query, Table, Router): ship a headless core that computes *what* to render, and let you decide *how* it looks. The repo's own fixed-size example virtualizes 10,000 rows with a plain `useVirtualizer` hook and a scroll container you provide:

```tsx
import * as React from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'

function RowVirtualizerFixed() {
  const parentRef = React.useRef(null)

  const rowVirtualizer = useVirtualizer({
    count: 10000,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 35,
    overscan: 5,
  })

  return (
    <div
      ref={parentRef}
      style={{
        height: `200px`,
        width: `400px`,
        overflow: 'auto',
      }}
    >
      <div
        style={{
          height: `${rowVirtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {rowVirtualizer.getVirtualItems().map((virtualItem) => (
          <div
            key={virtualItem.key}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: `${virtualItem.size}px`,
              transform: `translateY(${virtualItem.start}px)`,
            }}
          >
            Row {virtualItem.index}
          </div>
        ))}
      </div>
    </div>
  )
}
```

This snippet is taken directly from the official example in the repository. The key insight is that TanStack Virtual returns **measurements, not components** — you map `getVirtualItems()` into whatever markup you want, which is why it works identically in Solid, Vue, and Svelte. It also ships the features the other two lack: sticky items, window-scrolling utilities (`useWindowVirtualizer`), scroll-margin handling, and dynamic measurement where sizes are read from the DOM rather than estimated. At 10–15 kB it is also the only one of the three that is deliberately headless rather than component-opinionated.

**The trade-off:** you write more glue. There is no ready-made `<List>` component — you build the wrapper, the spacer, and the row rendering yourself. Teams that want a drop-in component may find react-window's API faster to adopt.

## react-window — Tiny, Battle-Tested, Rewritten for v2

react-window was created by Brian Vaughn (who also wrote react-virtualized) as a smaller, faster, more accessible replacement for it. It renders lists and grids efficiently and is used in production by React DevTools and the Replay browser. Version 2.3.0 (current) introduced a **completely new API** compared to the classic v1 `FixedSizeList`/`VariableSizeList` components: you now pass a `rowComponent` plus `rowCount` and `rowHeight` to a single `List`:

```tsx
import { type RowComponentProps } from 'react-window';

function RowComponent({ index, names, style }: RowComponentProps<{ names: string[] }>) {
  return (
    <div className="flex items-center justify-between" style={style}>
      {names[index]}
      <div className="text-slate-500 text-xs">{`${index + 1} of ${names.length}`}</div>
    </div>
  );
}

<List
  rowComponent={RowComponent}
  rowProps={{ names: ['Ada', 'Grace', 'Linus', /* ... */] }}
  rowCount={10000}
  rowHeight={35}
  style={{ height: '400px', width: '100%' }}
/>
```

The pattern above follows the documented v2 props — the row component receives `index` and `style` by default plus anything you pass through `rowProps`. `rowHeight` accepts a number, a percentage string, a function returning pixels, or the `useDynamicRowHeight` hook's cache (though the docs warn dynamic heights are less efficient than predetermined sizes). The v2 rewrite also brought the `List`/`Grid` API together, `listRef` for imperative scrolling, `onRowsRendered` callbacks, and a `defaultHeight` prop that matters for server rendering.

**The trade-off:** React-only, and the v2 API break means old v1 tutorials and Stack Overflow answers (`FixedSizeList` everywhere) no longer apply. If you are on v1, budget a migration pass.

## react-virtualized — The Legacy You Should Not Adopt

react-virtualized is the granddaddy of React windowing — 27,080 stars — and its feature list (AutoSizer, CellMeasurer, Masonry, Collection, Table, MultiGrid, ArrowKeyStepper) is the most complete of the three. The classic pattern looks like this, straight from the repo's List example:

```jsx
<List
  height={300}
  rowCount={1000}
  rowHeight={50}
  overscanRowCount={10}
  rowRenderer={({ index, key, style }) => (
    <div key={key} style={style}>{list[index]}</div>
  )}
/>
```

The problem is momentum. The last push was **January 2025** — 18+ months without meaningful activity as of this writing — and the official docs describe the project as being in maintenance mode. Its API is class-component era (the examples use `React.PureComponent` and PropTypes), it pulls in dependencies like `immutable` in its examples, and its maintainer has publicly steered users to react-window and TanStack Virtual. **If you are starting a project today, do not build on it.** If you maintain a legacy app on it, it still works — but treat it as frozen, and plan a migration whenever you next touch the virtualized list code.

## Common Pitfalls and Migration Gotchas

1. **Fixed heights are the default assumption everywhere.** TanStack Virtual needs `estimateSize` only as an initial guess (it measures and corrects); react-window's `rowHeight` is exact unless you use `useDynamicRowHeight`; react-virtualized's `rowHeight` is exact unless wrapped in CellMeasurer. Predictable heights keep scrolling smooth — prefer fixed sizes unless content genuinely varies.
2. **Overscan tuning is a real performance lever.** Too little overscan and fast scrolls show blank rows; too much and you render rows the user never sees. Start with 5–10 rows (TanStack's example uses 5) and increase only if you see white flashes.
3. **Scroll position loss on data change or resize.** When rows are added/removed above the viewport or the container resizes, naive implementations jump. react-window's `listRef` offers imperative scroll APIs; TanStack Virtual exposes `scrollToIndex`; react-virtualized has `scrollToIndex` too. Persist and restore scroll offsets explicitly in list-heavy apps.
4. **Accessibility is your job, not the library's.** Virtualized lists often break find-in-page, screen-reader row announcements, and keyboard navigation. TanStack Virtual's headless design makes ARIA your responsibility; react-window's v2 docs note `rowProps` must not contain `ariaAttributes` or `index`/`style`. Test with a screen reader before shipping.
5. **react-window v1 → v2 is a breaking rewrite.** `FixedSizeList`, `VariableSizeList`, and `areEqual` are gone; the `List` + `rowComponent` model replaces them. Run the official migration guide and audit every `itemSize`/`itemCount` prop.
6. **Don't virtualize everything.** Lists under ~200 rows render fine without windowing. Virtualization adds measurement complexity, breaks browser search, and complicates layout — apply it when it pays, which is exactly what the [React component library comparisons](../2026-08-16-shadcn-ui-vs-mantine-vs-chakra-react-component-libraries-comparison/) in our ecosystem guides also recommend for table-heavy UIs.

For adjacent data-display decisions, see our [JavaScript data grid comparison (TanStack Table vs AG Grid vs Grid.js)](../2026-08-12-tanstack-table-vs-ag-grid-vs-gridjs-javascript-data-grid-comparison/), the [React data fetching guide](../2026-08-11-tanstack-query-vs-swr-vs-rtk-query-react-data-fetching-comparison/), and the [JavaScript form libraries roundup](../2026-07-05-javascript-form-libraries-react-hook-form-formik-tanstack-final-form/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "JavaScript Virtual Scrolling in 2026: TanStack Virtual vs react-window vs react-virtualized",
  "description": "Compare TanStack Virtual, react-window v2, and react-virtualized for JavaScript virtual scrolling. Live GitHub stats, code examples, decision matrix, and migration pitfalls.",
  "datePublished": "2026-08-17",
  "dateModified": "2026-08-17",
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

**What is virtual scrolling (windowing)?**
Virtual scrolling renders only the items currently visible in the viewport — plus a small overscan buffer — instead of mounting every item in a large list. This keeps DOM size, memory usage, and initial paint time constant no matter how many rows your data has.

**Should I still use react-virtualized in 2026?**
Only for existing legacy codebases. The project has been in maintenance mode since January 2025 with no meaningful releases, its API is class-component era, and its own maintainer built react-window as its replacement. New projects should use TanStack Virtual or react-window.

**What is the difference between TanStack Virtual and react-window?**
TanStack Virtual is a headless, framework-agnostic hook (React, Solid, Vue, Svelte, vanilla) that returns measurements you render yourself, with dynamic sizing, sticky items, and window-scrolling built in. react-window is a React-only component library whose v2 `List` takes a `rowComponent`, `rowCount`, and `rowHeight` — less glue code, but React-only and less flexible.

**Does virtual scrolling work with dynamic row heights?**
Yes. TanStack Virtual measures rows from the DOM and corrects estimates automatically. react-window v2 offers `useDynamicRowHeight` (less efficient than fixed heights, per its docs). react-virtualized requires wrapping rows in `CellMeasurer`. Fixed heights remain the fastest option in all three.

**Which library has the smallest bundle size?**
react-window is the smallest of the three and advertises its tiny size; TanStack Virtual ships at roughly 10–15 kB; react-virtualized is the heaviest, with several subcomponents and extra dependencies. For a single-list use case, react-window or TanStack Virtual are both reasonable.

**Does TanStack Virtual work with Vue or Svelte?**
Yes. TanStack Virtual is framework-agnostic — the same core powers `@tanstack/react-virtual`, `@tanstack/vue-virtual`, `@tanstack/svelte-virtual`, and `@tanstack/solid-virtual`, so a team that spans frameworks can share the mental model.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
