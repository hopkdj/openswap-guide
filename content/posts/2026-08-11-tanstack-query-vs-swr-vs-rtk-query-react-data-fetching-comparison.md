---
title: "TanStack Query vs SWR vs RTK Query in 2026: Which React Data Fetching Library Should You Actually Use?"
date: "2026-08-11"
tags: ["typescript", "react", "frontend", "data-fetching", "developer-tools"]
draft: false
cover: "/img/screenshots/tanstack-query-data-fetching.jpg"
---

Your React app works. It fetches data, shows spinners, and somehow ships. But look closer: every component fetches on mount, the same endpoint is requested six times on one screen, and a background refetch blows away a form the user is mid-way through typing. That's not a React problem — it's a server-state problem, and the three dominant libraries in 2026 solve it very differently. **TanStack Query** (50,106 stars, updated August 2026), **SWR** (32,456 stars, by Vercel), and **RTK Query** (part of Redux Toolkit, 11,223 stars) each make different bets about how much framework you want. This guide compares them with real code from their official docs, real trade-offs, and a clear verdict for your stack.

## TL;DR / Quick Verdict

**Choose TanStack Query if** you want the most powerful, framework-agnostic server-state solution with excellent devtools, mutation support, and incremental loading — it's the default choice for most new apps in 2026. **Choose SWR if** you want the smallest, simplest hook that's still production-proven — ideal for light apps and SSR with Next.js, and its stale-while-revalidate behavior gives an instant cached UI. **Choose RTK Query if** you're already committed to Redux Toolkit and want your server cache and client state in one store with generated hooks. My honest recommendation: **TanStack Query for anything non-trivial, SWR for minimal apps, RTK Query only if Redux is already your religion.**

## The Quick Comparison

| Dimension | TanStack Query | SWR | RTK Query |
|---|---|---|---|
| GitHub stars / activity | 50,106⭐, updated 2026-08 | 32,456⭐, updated 2026-08 | 11,223⭐ (redux-toolkit), updated 2026-08 |
| Maintainer | TanStack (Tanner Linsley) | Vercel | Redux core team |
| License | MIT | MIT | MIT |
| Framework support | React, Vue, Svelte, Solid, Angular | React (official), others via community | React (official), framework-agnostic core |
| Bundle size (min+gzip) | ~13 kB (React) | ~4.3 kB | ~11 kB + Redux (~4 kB) |
| Cache key model | Query keys (array, serializable) | String keys + fetcher args | Endpoint + arg serialization |
| Mutations | First-class `useMutation`, optimistic updates | Manual via `mutate` + rollback | First-class `useMutation`, optimistic updates |
| Devtools | Excellent (time-travel, inspect cache) | Minimal (SWR DevTools beta) | Redux DevTools (via store) |
| SSR / SSG | First-class, `initialData` / hydration | Excellent (Next.js tight integration) | Via `initiate` thunks + hydration |
| Infinite/paginated queries | First-class (`useInfiniteQuery`) | Manual (`useSWRInfinite`) | Manual (via endpoints) |
| Learning curve | Moderate (query keys, staleTime) | Low (one hook) | Moderate-high (Redux concepts needed) |
| Best for | Complex server state, big apps | Simple apps, Next.js, minimal deps | Existing Redux codebases |

## The Decision Matrix

| Use Case | Recommended Tool | Why |
|---|---|---|
| New greenfield React app with complex server state | TanStack Query | Full mutation + caching + devtools story, no lock-in to Redux |
| Next.js app where SSR/ISR matters most | SWR | Built by Vercel, deepest Next.js integration, tiny footprint |
| Existing app already on Redux Toolkit | RTK Query | Same store, same middleware, generated hooks, minimal new concepts |
| Simple dashboard with a few GET endpoints | SWR | One hook, automatic dedup and focus revalidation |
| Optimistic UI with heavy mutations | TanStack Query | `useMutation` + `onMutate` rollback pattern is the best documented |
| Multi-framework codebase (Vue + React) | TanStack Query | Only one of the three with first-class multi-framework support |

## TanStack Query — The Server-State Powerhouse

TanStack Query (formerly React Query) treats server state as fundamentally different from client state: it's asynchronous, owned by the server, and shared across components. The core idea is the **query key** — a serializable array that uniquely identifies a query — paired with a `queryFn` that actually fetches:

```tsx
import {
  useQuery,
  useMutation,
  useQueryClient,
  QueryClient,
  QueryClientProvider,
} from '@tanstack/react-query'
import { getTodos, postTodo } from '../my-api'

// Create a client
const queryClient = new QueryClient()

function App() {
  return (
    // Provide the client to your App
    <QueryClientProvider client={queryClient}>
      <Todos />
    </QueryClientProvider>
  )
}

function Todos() {
  // Access the client
  const queryClient = useQueryClient()

  // Queries
  const query = useQuery({ queryKey: ['todos'], queryFn: getTodos })

  // Mutations
  const mutation = useMutation({
    mutationFn: postTodo,
    onSuccess: () => {
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: ['todos'] })
    },
  })

  return (
    <div>
      <ul>
        {query.data?.map((todo) => (
          <li key={todo.id}>{todo.title}</li>
        ))}
      </ul>
      <button
        onClick={() => mutation.mutate({ title: 'New Todo' })}
        disabled={mutation.isPending}
      >
        {mutation.isPending ? 'Adding...' : 'Add Todo'}
      </button>
    </div>
  )
}
```

The `staleTime` / `gcTime` model is what separates it from a naive `useEffect` fetch: you tell React Query how fresh your data is, and it decides when to refetch in the background instead of blocking the UI. **This single concept removes more loading-spinner bugs than any other feature in the library.** Query cancellation, retry with exponential backoff, and `useInfiniteQuery` for paginated lists are all built in. The DevTools browser extension lets you inspect every query's state, keys, and timestamps — invaluable when a stale cache mystery shows up in production.

## SWR — The Minimal Stale-While-Revalidate Hook

SWR gets its name from the HTTP cache strategy *stale-while-revalidate* (RFC 5861): return the cached data instantly, revalidate in the background, and swap in fresh data when it arrives. The whole library is one hook with a tiny footprint, which is why it powers Vercel's own dashboards:

```js
import useSWR from 'swr'

const fetcher = (...args) => fetch(...args).then((res) => res.json())

function Profile() {
  const { data, error, isLoading } = useSWR('/api/user', fetcher)

  if (error) return <div>failed to load</div>
  if (isLoading) return <div>loading...</div>
  return <div>hello {data.name}!</div>
}
```

That's the entire API surface for the 90% case: a key, a fetcher, and a state object. SWR auto-deduplicates concurrent requests for the same key, revalidates on window focus and network reconnection by default, and supports polling, pagination, scroll-position recovery, optimistic UI via `mutate`, and React Suspense — all with the default configuration often being good enough. Its tightest integration is with Next.js, where `fallback` data from `getServerSideProps` hydrates the cache so the first paint has real data. The trade-off: anything beyond GET-heavy CRUD requires manual composition, and mutations have no dedicated primitive — you call `mutate` yourself and handle rollback manually.

## RTK Query — Server State Inside Your Redux Store

RTK Query is the official data-fetching layer of Redux Toolkit. Instead of a hook wrapping a fetch, you declare a **service** with `createApi`, and RTK Query generates typed hooks, cache lifecycle, and store integration for you:

```ts
import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react'
import type { Pokemon } from './types'

// Define a service using a base URL and expected endpoints
export const pokemonApi = createApi({
  reducerPath: 'pokemonApi',
  baseQuery: fetchBaseQuery({ baseUrl: 'https://pokeapi.co/api/v2/' }),
  endpoints: (build) => ({
    getPokemonByName: build.query<Pokemon, string>({
      query: (name) => `pokemon/${name}`,
    }),
  }),
})

// Export hooks for usage in functional components, which are
// auto-generated based on the defined endpoints
export const { useGetPokemonByNameQuery } = pokemonApi
```

Because everything flows through the Redux store, you get normalised cache tags, `provideTags`/`invalidateTags` for automatic invalidation of related queries, optimistic updates via `onQueryStarted` + `queryFulfilled`, and streamed updates with `onCacheEntryAdded` — all visible in Redux DevTools alongside your client state. That's the real value proposition: **one store, one mental model, one debugging experience.** The cost is conceptual: you must already accept Redux's store/middleware/selector model, and the generated-hook ergonomics are more ceremony than SWR's single line. For teams that live in Redux, it's a natural extension; for teams that left Redux to escape boilerplate, it's a reason to stay away.

## Common Pitfalls and Migration Traps

1. **Don't mix multiple server-state libraries.** Pick one and standardize. Two libraries mean two caches, two invalidation systems, and duplicate requests to the same endpoint — the exact problem they're supposed to solve.
2. **Learn `staleTime` before you ship.** The default `staleTime` of 0 in TanStack Query means every mount refetches. Set a sensible `staleTime` (30s-5min depending on data volatility) or your API will get hammered and your UI will flicker.
3. **Query keys are contracts.** A key like `['users']` vs `['users', id]` is easy to get wrong; an inconsistent key means cache misses and refetch storms. Define key factories and reuse them.
4. **Don't fetch in `useEffect` anymore.** All three libraries deduplicate and cache; a hand-rolled `useEffect` fetch in a component tree does neither and will fire N times for N mounts.
5. **Be careful with JSON-serializable cache keys.** Redux Toolkit requires serializable state by design; non-serializable values in query args (functions, class instances) break persistence and devtools in RTK Query, and cause subtle equality bugs in TanStack Query's structural sharing.
6. **SSR hydration gotcha:** fetching on the server and re-fetching on the client defeats SSR. Use `initialData`/`fallback` hydration in all three — SWR's Next.js integration is the smoothest, but TanStack's `HydrationBoundary` and RTK's `initiate` thunks both work well once configured.
7. **Optimistic updates must be rolled back.** If you optimistically mutate without handling failure, your UI lies to users. All three support rollback — wire it up before you rely on it.


For more on how server-state libraries fit into the broader React ecosystem, see our [JavaScript state management comparison](../2026-07-05-javascript-state-management-redux-zustand-jotai-mobx-pinia/) and our [GraphQL server libraries guide](../2026-06-20-graphql-server-libraries-apollo-yoga-mercurius-strawberry-hotchocolate/). If you are evaluating the testing side of a data-heavy app, our [JavaScript testing frameworks comparison](../2026-07-21-javascript-testing-frameworks-vitest-jest-playwright/) covers the other half of the toolchain.

## FAQ

**What is the difference between TanStack Query and React Query?**
They are the same project. React Query was renamed to TanStack Query when the library expanded beyond React to support Vue, Svelte, Solid, and Angular. The React-specific package is `@tanstack/react-query`, and the docs and GitHub repo moved to the TanStack org.

**Is SWR only for Next.js?**
No. SWR is a React hooks library that works in any React app (Vite, Create React App, React Native, Remix). It has especially tight integration with Next.js because both are maintained by Vercel, but it is not Next.js-only.

**Does RTK Query require the full Redux setup?**
RTK Query is part of Redux Toolkit, so yes — it requires the Redux store and provider. There is no standalone version. If you aren't already using Redux, TanStack Query or SWR will be much less invasive.

**Which library has the best TypeScript support in 2026?**
All three are fully typed. TanStack Query generates the most precise types for query data (including `data` being `undefined` until loaded, forcing you to handle the loading state); RTK Query generates hook types directly from endpoint definitions; SWR's types are solid but simpler.

**Can I use optimistic updates with SWR?**
Yes, via the `mutate` function with an optimistic data value and a rollback function for the error case. It's manual — SWR has no dedicated mutation primitive — but the pattern is documented and works well for single-key updates.

**What bundle size should I expect?**
SWR is the smallest at roughly 4.3 kB min+gzip. TanStack Query's React package is around 13 kB. RTK Query adds about 11 kB on top of Redux Toolkit (~4 kB for redux core). For a tiny landing page, SWR wins; for a large application, bundle size is rarely the deciding factor.

**Which one should I pick for a new project in 2026?**
If you're starting fresh and your app has real server state (lists, detail pages, mutations, pagination), pick TanStack Query. If you want minimal dependencies and mostly read data, pick SWR. If you already use Redux Toolkit, pick RTK Query. All three are actively maintained with releases in August 2026.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "TanStack Query vs SWR vs RTK Query in 2026: Which React Data Fetching Library Should You Actually Use?",
  "description": "Deep comparison of TanStack Query, SWR, and RTK Query for React data fetching in 2026 with real code, benchmark data, and clear recommendations.",
  "datePublished": "2026-08-11",
  "dateModified": "2026-08-11",
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
