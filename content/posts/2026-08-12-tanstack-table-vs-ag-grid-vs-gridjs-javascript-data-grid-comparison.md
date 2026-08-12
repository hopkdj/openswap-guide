---
title: "TanStack Table vs AG Grid vs Grid.js in 2026: Which JavaScript Data Grid Should You Use?"
date: "2026-08-12"
tags: ["javascript", "data-grid", "react", "frontend", "developer-tools", "datatables"]
draft: false
cover: "/img/screenshots/gridjs-demo.jpg"
---

Every dashboard eventually needs to show a table — and then the table needs sorting, filtering, pagination, and sticky headers, and suddenly your "simple table" is a weekend project. The JavaScript data grid ecosystem has three serious answers with very different philosophies: **TanStack Table (28,316 stars)** is the headless library that gives you total control over markup in exchange for writing your own DOM, **AG Grid (15,530 stars)** is the batteries-included enterprise grid with 100+ features out of the box, and **Grid.js (4,686 stars)** is the lightweight, framework-agnostic grid that nails the 80% case in a single dependency. Choose wrong and you either re-implement virtualization by hand or drag a 3 MB enterprise bundle into a page that needed 30 rows.

The numbers below are live GitHub data from August 2026. The decision matrix in the middle of this article is the part worth copying into your team's RFC.

## TL;DR: Quick Verdict

- **Choose TanStack Table** if you use React (or Vue/Svelte/Solid) and want full control — headless means you style every pixel, and the performance model is the best of the three. It is the default for modern React dashboards.
- **Choose AG Grid** if you need enterprise features today — row grouping, pivot, master/detail, Excel export, 20+ chart types — without a multi-month build. You pay in bundle size (1 MB+ full build) and licensing complexity (MIT core, commercial modules).
- **Choose Grid.js** if you need one grid for a plain JavaScript page, a small admin panel, or a non-React app — it is the fastest to integrate and the lightest of the three.

## The Contenders at a Glance

| Dimension | TanStack Table | AG Grid | Grid.js |
|---|---|---|---|
| **GitHub stars** | 28,316 | 15,530 | 4,686 |
| **Last push** | 2026-08-11 | 2026-08-12 | 2026-01-29 |
| **License** | MIT | MIT core + commercial modules | Apache-2.0 |
| **Architecture** | Headless (bring your own markup) | Full grid component | Self-contained grid component |
| **Framework support** | React, Vue, Svelte, Solid, Lit, vanilla | React, Angular, Vue, vanilla | Vanilla JS (framework wrappers via adapter) |
| **Bundle size** | ~15 kB core (headless) | ~1 MB+ full, ~350 kB community | ~50 kB minified |
| **Virtualization** | First-class (TanStack Virtual) | Built-in | Built-in |
| **Sorting/filtering/pagination** | Manual (you wire it) | Built-in | Built-in |
| **Row grouping / pivot** | Manual | Built-in (enterprise) | No |
| **Excel/CSV export** | Manual | Built-in (CSV free, Excel enterprise) | CSV export |
| **Theme system** | CSS modules / Tailwind | 30+ built-in themes, CSS vars | Mermaid theme + custom CSS |
| **Best for** | React apps needing full control | Enterprise analytics & finance grids | Small admin panels, vanilla JS |

## Decision Matrix

| Use Case | Recommended Tool | Reason |
|---|---|---|
| React dashboard with custom design system | **TanStack Table** | Headless API composes with Tailwind/MUI; no fighting a vendor theme |
| Enterprise grid with grouping, pivot, Excel export | **AG Grid** | 100+ built-in features; the community edition covers most needs |
| Admin panel in plain JavaScript (no framework) | **Grid.js** | One dependency, clean API, zero build friction |
| Vue or Svelte project | **TanStack Table** | Official adapters for all major frameworks with the same headless core |
| Page with 100k+ rows | **TanStack Table** | TanStack Virtual row virtualization is the fastest option of the three |
| Team with aggressive timeline and wide feature scope | **AG Grid** | Features you would spend months building ship in one `gridOptions` object |
| Bundle-budget-sensitive public page | **Grid.js** | ~50 kB all-in versus 1 MB+ for a full AG Grid build |

## TanStack Table: The Headless Powerhouse

TanStack Table (formerly React Table) made the bet that grids should not render anything — just give you the state machine (sorting, filtering, pagination, column visibility, row selection) and let you own the markup. That bet paid off: at **28,316 stars** with an August 2026 release, it is the default choice for modern React dashboards, and the same headless core now powers Vue, Svelte, Solid, and Lit via official adapters.

```tsx
import { useReactTable, getCoreRowModel, flexRender, createColumnHelper } from '@tanstack/react-table';

const columnHelper = createColumnHelper<User>();

const columns = [
  columnHelper.accessor('firstName', { header: 'First Name' }),
  columnHelper.accessor('lastName', { header: 'Last Name' }),
];

function Table({ data }: { data: User[] }) {
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <table>
      <thead>
        {table.getHeaderGroups().map(headerGroup => (
          <tr key={headerGroup.id}>
            {headerGroup.headers.map(header => (
              <th key={header.id}>
                {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
              </th>
            ))}
          </tr>
        ))}
      </thead>
      <tbody>
        {table.getRowModel().rows.map(row => (
          <tr key={row.id}>
            {row.getVisibleCells().map(cell => (
              <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

The upside is total freedom: your table is a semantic `<table>` (or divs, or whatever), your design system styles it, and there is no vendor theme to override. Sorting, filtering, and pagination are opt-in row models (`getSortedRowModel`, `getFilteredRowModel`, `getPaginationRowModel`) that compose predictably. For very large datasets, TanStack Virtual integrates in one line and gives the fastest scrolling of the three.

The cost is that everything is manual. There is no built-in export, no column menu, no inline editing — you build those. The ecosystem around it (TanStack Query for data fetching, TanStack Form for editing) is excellent, but it is a framework commitment: you are adopting the TanStack philosophy across your data layer. Teams that just want "a grid that works" should look elsewhere.

## AG Grid: The Enterprise Feature Factory

AG Grid is the most feature-complete open-source data grid in existence. The community edition alone includes sorting, filtering, pagination, row grouping, pivoting, master/detail, tree data, custom cell renderers, and CSV export — features that take months to build by hand. The enterprise modules add Excel export, aggregation, range selection, charting, and more under a commercial license.

```js
// Grid Options: Contains all of the Data Grid configurations
const gridOptions = {
    // Row Data: The data to be displayed.
    rowData: [
        { make: 'Tesla', model: 'Model Y', price: 64950, electric: true },
        { make: 'Ford', model: 'F-Series', price: 33850, electric: false },
        { make: 'Toyota', model: 'Corolla', price: 29600, electric: false },
    ],
    // Column Definitions: Defines the columns to be displayed.
    columnDefs: [{ field: 'make' }, { field: 'model' }, { field: 'price' }, { field: 'electric' }],
};

// Create the Data Grid
const myGridElement = document.querySelector('#myGrid');
agGrid.createGrid(myGridElement, gridOptions);
```

With **15,530 stars** and an active August 2026 release, AG Grid is battle-tested in finance, healthcare, and analytics products where grids are the core UI. It works with React, Angular, Vue, and plain JavaScript through the same `createGrid` API. Performance is production-grade: row/column virtualization, server-side row models for million-row datasets, and incremental updates via `api.applyTransaction` are all built in.

The trade-offs are real. The full community build is heavy — roughly **350 kB minified** for community, over **1 MB** with enterprise modules — and tree-shaking is difficult because everything hangs off one API surface. The license split (MIT core, paid enterprise modules) confuses procurement in some orgs, though the community edition covers most self-hosted and SaaS needs. And its theming, while extensive, is opinionated: expect to spend time mapping your design tokens onto AG Grid's CSS variables rather than the reverse.

## Grid.js: The Lightweight All-Rounder

Grid.js, created by Afshin Mehrabani, is the answer for the 80% of tables that just need to look decent and work: sort, search, paginate, done. It is framework-agnostic by design — a single self-contained component you render into any container — which makes it the fastest grid to integrate in the entire ecosystem.

```js
import { Grid } from 'gridjs';
import 'gridjs/dist/theme/mermaid.css';

new Grid({
  columns: ['Name', 'Email', 'Phone'],
  data: [
    ['John', 'john@example.com', '(353) 01 222 3333'],
    ['Mark', 'mark@gmail.com', '(01) 22 888 4444'],
  ],
  sort: true,
  search: true,
  pagination: {
    enabled: true,
    limit: 3,
  },
}).render(document.getElementById('wrapper'));
```

That is the whole integration: import, configure, render. Grid.js supports server-side data via a `server` configuration with a `url` and `then` handler, CSV export, styled cells with custom formatters, and a clean plugin system. At **4,686 stars** it is the smallest community of the three, and development has slowed — the last push was **January 2026** — but the library is stable and complete for its scope.

The limitations are clear: no row grouping, no pivot, no master/detail, no framework-specific ergonomics (you manage re-renders yourself in React via `grid.updateConfig`). For a small admin panel, an internal tool, or a vanilla JS page, it is often the right call — and at roughly **50 kB minified**, it is the only one of the three you can drop into a public page without a performance conversation.

## Migration and Coexistence Strategies

**From Grid.js to TanStack Table.** The data shapes are compatible (arrays of rows), but everything else changes: Grid.js's config-object API becomes a headless state machine, and your `search: true` becomes `getFilteredRowModel` plus a search input you wire yourself. Plan for a day per grid if your Grid.js usage is config-only, more if you used custom formatters.

**From AG Grid to TanStack Table.** This is the expensive migration. AG Grid's `columnDefs` map cleanly to TanStack `createColumnHelper`, but grouping, export, and cell editing have no direct equivalents — you rebuild them. Budget is realistic only when you are also redesigning the UI; otherwise the migration cost exceeds the benefit of the smaller bundle.

**Coexistence in a larger app.** Nothing stops you from running AG Grid for the finance module and Grid.js for the admin module — they do not share state or DOM. The one rule: never render two grids over the same container element, and always call `grid.destroy()` / `api.destroy()` in component teardown, or you will leak listeners and get duplicate render errors on hot reload.

**Performance checklist for large datasets.** Whatever you choose: (1) supply stable row IDs — TanStack and AG Grid both dedupe and update by identity; (2) use `memo` on row renderers — all three re-render visible rows on every sort; (3) avoid putting new object literals in `columnDefs` on each render, or React reconciliation will thrash; (4) measure with 10k rows before optimizing for 100k.

## Common Pitfalls and Performance Traps

1. **Missing stable row IDs.** Without `getRowId`, TanStack Table treats rows by index and AG Grid by reference — sorting then editing silently corrupts row state in both.
2. **Full AG Grid import in a bundler.** `import { Grid } from 'ag-grid-community'` pulls the whole package. Use the module system (`ag-grid-community/dist/package/main.cjs.js`) or the framework-specific packages to enable tree-shaking; the naive import is why AG Grid apps ship 1 MB of grid.
3. **Grid.js in React without lifecycle handling.** Grid.js manages its own DOM; in React you must create it in `useEffect` and call `destroy()` in cleanup, or Strict Mode double-invocation will render two grids.
4. **Virtualization hidden cost.** TanStack Virtual's row windowing means your CSS must not depend on row height variance — mixed-height rows need `estimateSize` tuning or you get scroll jank.
5. **Sorting numbers as strings.** All three sort lexicographically by default on raw values. Coerce numeric columns with a `sortingFn: 'alphanumeric'` (TanStack), `comparator` (Grid.js), or numeric cell type (AG Grid) or "10" will sort before "2".
6. **Accessibility defaults.** TanStack Table gives you semantic `<table>` by default (good), but keyboard navigation, ARIA sorting states, and focus management are all manual. AG Grid ships these built in — factor that into your effort estimate.

## FAQ

**What is the difference between TanStack Table and AG Grid?**
TanStack Table is headless — it manages sorting, filtering, pagination, and selection state but renders nothing, so you write the markup and style it with your design system. AG Grid is a complete grid component with built-in rendering, theming, grouping, pivoting, and export features.

**Is AG Grid free to use?**
The community edition is MIT licensed and free, including sorting, filtering, pagination, grouping, and CSV export. Enterprise features (Excel export, pivot, range selection, charting) require a commercial license. Grid.js is fully Apache-2.0.

**Which data grid is the smallest?**
Grid.js at roughly 50 kB minified. TanStack Table's headless core is around 15 kB but you add your own rendering. AG Grid's community build is about 350 kB, and over 1 MB with enterprise modules.

**Does TanStack Table work with Vue or Svelte?**
Yes. TanStack Table ships official adapters for React, Vue, Svelte, Solid, and Lit, all built on the same headless core, so your column definitions and row models are portable across frameworks.

**Can these grids handle 100,000 rows?**
TanStack Table with TanStack Virtual handles 100k+ rows smoothly because it only renders visible rows. AG Grid supports million-row datasets with its server-side row model. Grid.js is fine up to tens of thousands of rows in the browser.

**Which grid should I use for a quick admin panel?**
Grid.js. One dependency, a single `new Grid({...}).render()` call, and built-in sort, search, and pagination cover most admin needs in under an hour. Move to TanStack Table when you need deep customization, or AG Grid when you need enterprise features.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "TanStack Table vs AG Grid vs Grid.js in 2026: Which JavaScript Data Grid Should You Use?",
  "description": "Deep comparison of TanStack Table, AG Grid, and Grid.js for JavaScript data grids in 2026. Architecture, bundle sizes, licensing, migration strategies, and a use-case decision matrix with live GitHub data.",
  "datePublished": "2026-08-12",
  "dateModified": "2026-08-12",
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

Pairing a grid with the right data layer matters more than the grid itself — see our [TanStack Query vs SWR vs RTK Query comparison](../2026-08-11-tanstack-query-vs-swr-vs-rtk-query-react-data-fetching-comparison/) and the [React form libraries guide](../2026-07-05-javascript-form-libraries-react-hook-form-formik-tanstack-final-form/). For dashboard state, our [state management shootout](../2026-07-05-javascript-state-management-redux-zustand-jotai-mobx-pinia/) covers the Redux/Zustand/Jotai landscape.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
