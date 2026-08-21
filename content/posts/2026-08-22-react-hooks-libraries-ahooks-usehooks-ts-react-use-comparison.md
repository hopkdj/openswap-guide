---
title: "ahooks vs usehooks-ts vs react-use in 2026: Which React Hooks Library Should You Actually Use?"
date: "2026-08-22"
tags: ["react", "javascript", "typescript", "frontend", "hooks"]
draft: false
cover: "/img/screenshots/react-hooks-cover.jpg"
---

If you have written more than one `useEffect` that manually subscribes to `window.addEventListener("resize")` and then forgot to clean it up, you already know why React hooks libraries exist. The three most popular collections — **ahooks** (14,979 stars), **usehooks-ts** (7,850 stars), and **react-use** (44,020 stars) — collectively save thousands of teams from re-implementing the same debounce, media query, clipboard, and request lifecycle logic. But they take radically different approaches to the same problem, and picking the wrong one means either carrying 200 hooks you will never touch or hand-rolling the one hook you actually needed.

## Quick Verdict: Which Hooks Library Should You Use?

**If you build data-heavy admin panels and dashboards, choose ahooks** — its `useRequest` wrapper alone (loading, polling, retry, pagination, caching) replaces most of your fetch boilerplate. **If you want a small, tree-shakable, TypeScript-first collection for a public-facing app, choose usehooks-ts** — it is the most bundle-conscious of the three and ships server-side-rendering-safe utilities out of the box. **If you want the widest coverage of browser sensor behavior** — media queries, network state, device orientation, mouse position — **choose react-use**, which is the largest collection at roughly 200 hooks. Do not install all three; their APIs overlap heavily and your bundle will thank you for picking one.

## Head-to-Head: Feature Comparison

| Feature | ahooks | usehooks-ts | react-use |
|---|---|---|---|
| GitHub stars (Aug 2026) | 14,979 | 7,850 | 44,020 |
| Last push | 2026-08-09 | 2026-08-14 | 2026-06-10 |
| Approx. hook count | 80+ | 60+ | 200+ |
| Signature feature | `useRequest` (polling/retry/pagination/cache) | SSR-safe localStorage & media queries | Sensor hooks (network, media, orientation) |
| Written in TypeScript | Yes | Yes | Yes |
| Tree-shakable ESM | Yes | Yes (explicit goal) | Partial |
| SSR support | Yes | Yes (designed for it) | Limited (guard with `isBrowser`) |
| License | MIT | MIT | MIT |
| Maintainer model | Alibaba team | Community fork (juliencrn) | Streamich + community |
| Ideal project | Admin consoles, data dashboards | Library components, SSR apps | Prototypes, sensor-heavy UIs |

All three are MIT-licensed and actively maintained; react-use's star count reflects its age and breadth more than recent velocity, so do not treat it as the "safest" choice purely on popularity.

## Decision Matrix: Match the Library to Your Use Case

| Use Case | Recommended Library | Why |
|---|---|---|
| Admin panel with tables, forms, and polling | **ahooks** | `useRequest` + `usePagination` + `useTable` cover the full data-fetching lifecycle |
| Next.js / Remix app that must not flash on hydration | **usehooks-ts** | Every hook is designed to be SSR-safe; `useLocalStorage` works during server render |
| A dashboard that reacts to screen size, online status, and device sensors | **react-use** | `useMedia`, `useNetworkState`, `useOrientation`, and `useMouse` are one import away |
| A component library you publish to npm | **usehooks-ts** | Minimal, typed, tree-shakable; your consumers only pay for what they import |
| You need a full request state machine (loading/error/data) without Redux | **ahooks** | `useRequest` replaces hand-rolled fetch state in most CRUD screens |
| Quick prototype, maximum hook coverage | **react-use** | 200+ hooks means whatever you need probably exists already |

## ahooks: The Enterprise Swiss Army Knife

ahooks is maintained by Alibaba and is the most "batteries included" of the three. It pairs naturally with the design-system components covered in our [React component libraries comparison](../2026-08-16-shadcn-ui-vs-mantine-vs-chakra-react-component-libraries-comparison/), where similar enterprise-minded trade-offs apply. Its headline feature is **`useRequest`**, a hook that manages the entire asynchronous request lifecycle: `loading`, `data`, `error`, manual `run`, polling, retry, pagination, and even a plugin system for caching and debouncing. For a CRUD-heavy admin interface, `useRequest` eliminates a surprising amount of code:

```tsx
import { useRequest } from 'ahooks';

function fetchUsers(params) {
  return fetch('/api/users', { body: JSON.stringify(params) })
    .then((res) => res.json());
}

function UserTable() {
  const { data, loading, run, refresh } = useRequest(fetchUsers, {
    pollingInterval: 30000, // refresh every 30s
    retryCount: 3,          // retry transient failures
    manual: true,
  });

  useEffect(() => { run({ page: 1 }); }, []);

  return (
    <div>
      <button onClick={refresh}>Refresh</button>
      {loading ? <Spinner /> : <Table rows={data?.rows ?? []} />}
    </div>
  );
}
```

Beyond `useRequest`, ahooks provides `usePagination` for server-side table pagination, `useVirtualList` for long lists, `useCountDown`, `useWebSocket`, and `useFusionTable`-style integrations for enterprise forms. The trade-off: the API surface is opinionated, and some hooks (especially the ones that wrap external libraries like Ant Design) assume you are building inside a specific ecosystem.

## usehooks-ts: The Tree-Shakable TypeScript Standard

usehooks-ts started as a community collection and became the de-facto "clean" option: fully typed, explicitly tree-shakable, and deliberately SSR-safe. The project moved to the ui.dev team in 2024 and, after a quiet 2025, the **juliencrn fork is now the actively maintained home** — which is itself a lesson about single-maintainer dependencies. Its README is explicit about the design goal: "fully tree-shakable (using the ESM version), meaning that you only import the hooks you need."

```tsx
import { useLocalStorage } from 'usehooks-ts';

function Component() {
  const [value, setValue] = useLocalStorage('my-localStorage-key', 0);
  // value is persisted across reloads; safe during SSR because the
  // hook defers to window.localStorage only in the browser
  return (
    <input
      value={value}
      onChange={(e) => setValue(Number(e.target.value))}
    />
  );
}
```

`useLocalStorage` is the classic example: in a hand-rolled implementation, most teams forget the `typeof window === "undefined"` guard and ship a hydration mismatch to production. usehooks-ts handles that internally, and its other hooks — `useMediaQuery`, `useEventListener`, `useDebounce`, `useToggle`, `useWindowSize` — follow the same conservative, typed pattern. If your team values predictability and bundle size over raw hook count, this is the collection to standardize on. TypeScript teams will also want to look at the [TypeScript utility types comparison](../2026-08-18-type-fest-vs-utility-types-vs-ts-toolbelt-typescript-utility-types-comparison/) we published for the type-level helpers that complement these runtime hooks.

## react-use: The 200-Hook Sensor Library

react-use is the oldest and largest of the three, a port of the `libreact` utilities with more than 200 hooks. Its superpower is the **sensor category**: hooks that track the browser environment and update state reactively. `useMedia` lets you mirror CSS media queries in JavaScript, which is the cleanest way to render different markup per breakpoint without CSS hacks:

```tsx
import { useMedia, useNetworkState } from 'react-use';

function StatusBar() {
  const isWide = useMedia('(min-width: 1024px)');
  const network = useNetworkState();

  return (
    <div>
      {isWide ? <FullLayout /> : <CompactLayout />}
      {network.online ? 'Online' : 'Offline'} — {network.effectiveType}
    </div>
  );
}
```

You also get `useMouse`, `useScroll`, `useBattery`, `useOrientation`, `usePageLeave`, `useStartTyping`, and dozens of state-management helpers like `useStateWithHistory` and `useMethods`. The catch is scope discipline: importing a handful of hooks is fine, but the package's sheer surface invites overuse, and the project's long history means some hooks still carry assumptions from the class-component era. For sensor-heavy UIs it is unmatched; for a tightly-controlled design system it is probably more than you want.

## Pitfalls: What Nobody Tells You About Hooks Libraries

1. **Hydration mismatches are the #1 production bug.** Any hook that touches `window`, `localStorage`, or `matchMedia` must be SSR-guarded. react-use historically requires a `isBrowser` check or a mounted state pattern; usehooks-ts handles it by design; ahooks is mostly safe but test the specific hook you use.
2. **Bundle size creeps in through re-exports.** With react-use, import from the package root and rely on tree-shaking; with usehooks-ts, prefer named imports of individual hooks. Run `vite-bundle-visualizer` or `webpack-bundle-analyzer` after adoption — a single `import { useMedia } from 'react-use'` should not pull the whole library into your chunk.
3. **Polling and refetch hooks leak when unmounted.** ahooks `useRequest` cleans up timers on unmount, but if you pass a `manual: false` + `pollingInterval` combination into a component that mounts and unmounts rapidly (tab switches, route changes), verify with React DevTools that no interval survives. Use `ready`/`refreshDeps` options to pause polling when the tab is hidden.
4. **The single-maintainer risk is real.** usehooks-ts's 2025 quiet period and its subsequent fork migration show what happens when a beloved library depends on one person. Before adopting any hook collection, check the issue tracker's response time — not just the star count.
5. **Don't mix libraries.** Two collections export similarly-named hooks (`useDebounce`, `useLocalStorage`) with subtly different option signatures. Standardizing on one avoids the "which debounce am I importing?" confusion that costs more time than the libraries save.
6. **Custom hooks are not a substitute for state management.** A library like ahooks' `useRequest` caches in memory and pairs well with the state-management patterns covered in our [JavaScript state management comparison](../2026-07-05-javascript-state-management-redux-zustand-jotai-mobx-pinia/); it is not a replacement for server state sync across tabs.

## FAQ

### Which React hooks library has the most stars in 2026?

**react-use** leads with roughly 44,020 GitHub stars, followed by **ahooks** at 14,979 and **usehooks-ts** at 7,850. Star counts reflect age and ecosystem reach more than maintenance velocity, so always cross-check the last push date and issue response time.

### What is ahooks' useRequest and why is it popular?

`useRequest` is ahooks' flagship hook for managing asynchronous requests: it exposes `loading`, `data`, `error`, `run`, `refresh`, and `cancel`, and supports polling, retry, pagination, caching, and debouncing through plugins. Teams use it to eliminate hand-written fetch state logic in admin panels and dashboards.

### Is usehooks-ts safe to use in Next.js or other SSR frameworks?

Yes — it is explicitly designed to be SSR-safe. Hooks like `useLocalStorage` and `useMediaQuery` guard against `window` access during server rendering, preventing the hydration mismatch errors that plague naive implementations.

### Can I use react-use with React 18 or React 19?

Yes, react-use works with modern React versions. For sensor hooks (`useMedia`, `useNetworkState`) prefer the most recent release, and wrap any hook that reads browser APIs in a mounted-state check when rendering on the server.

### Do I need a hooks library if my project only needs two utilities?

No. If you need fewer than a handful of hooks, copy the ten-line implementations into your own `hooks/` directory or vendor them from a permissive-license collection. The libraries pay off when you need consistent behavior across many components — or when the logic is subtle enough that a battle-tested implementation beats yours (debounce, local storage, media queries).

### Which library is best for a component library I publish on npm?

**usehooks-ts** is the strongest fit: it is TypeScript-first, tree-shakable, and SSR-safe, so downstream consumers only pay for the hooks they import and never inherit hydration bugs.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "ahooks vs usehooks-ts vs react-use in 2026: Which React Hooks Library Should You Actually Use?",
  "description": "Compare the three most popular React hooks libraries — ahooks, usehooks-ts, and react-use — by features, bundle size, SSR safety, and GitHub activity to pick the right one for your project in 2026.",
  "datePublished": "2026-08-22",
  "dateModified": "2026-08-22",
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
