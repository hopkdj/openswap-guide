---
title: "tRPC vs Elysia vs ts-rest in 2026: End-to-End Type-Safe TypeScript APIs Compared"
date: "2026-09-01"
tags: ["comparison", "guide", "typescript", "api", "rpc", "developer-tools"]
draft: false
cover: "/img/screenshots/elysia-type-safe-cover.jpg"
description: "Compare tRPC, Elysia, and ts-rest for end-to-end type-safe TypeScript APIs — RPC, framework, and contract-first approaches with real code, decision matrices, and migration guidance for 2026."
---

TypeScript's promise stops at the API boundary. Your frontend and backend may both be perfectly typed, but the moment a `fetch` crosses the wire, every type guarantee evaporates — a renamed field, a missing property, or a changed response shape turns into a runtime bug that ships to production. The three libraries in this comparison attack that exact gap: **tRPC** (40,564 stars) infers types straight from your server procedures, **Elysia** (19,039 stars) bakes end-to-end safety into a Bun-native web framework, and **ts-rest** (3,336 stars) keeps your REST contract as the single source of truth. All three eliminate the duplicated types and drift that plague every non-trivial full-stack TypeScript project.

## TL;DR — Quick Verdict

- **Choose tRPC** if you own both the frontend and backend and want zero-boilerplate procedure calls with inferred types — the fastest path from idea to working full-stack feature.
- **Choose Elysia** if you want a complete web framework with end-to-end safety built in — routes, validation, OpenAPI docs, and a typed client generated from one file, especially on Bun.
- **Choose ts-rest** if you must keep a pure REST API (third-party clients, public endpoints, OpenAPI consumers) but still want shared types and contract validation on both sides.

## Feature Comparison at a Glance

| Feature | tRPC | Elysia | ts-rest |
|---|---|---|---|
| GitHub stars (2026-09) | 40,564 | 19,039 | 3,336 |
| Core model | RPC procedures | Web framework + RPC client | Contract-first REST |
| Runtime | Node, Bun, Deno, edge | Bun-first (Node via adapter) | Node (Express, Fastify, NestJS) |
| Validation | Zod (recommended) | TypeBox / t.Object built-in | Zod (built-in support) |
| Code generation | None — types inferred | None — types inferred | None — contract shared |
| OpenAPI export | Via plugin (trpc-openapi) | Built-in (`app.toOpenAPI()`) | Via `@ts-rest/open-api` |
| Client style | `createTRPCProxyClient` | Eden Treaty (`edenTreaty`) | `initClient` from contract |
| Streaming / subscriptions | Yes (WS adapters) | Yes (SSE, WS) | SSE via adapters |
| Monorepo requirement | Recommended | Recommended | Required (shared contract) |
| License | MIT | MIT | MIT |
| Last push (2026) | Aug 31 | Aug 30 | Feb 06 |

## Decision Matrix — Use Case → Tool → Why

| Use Case | Recommended Tool | Reasoning |
|---|---|---|
| Next.js / full-stack app, minimal ceremony | tRPC | Type inference with zero codegen; drop-in for any React/Next project |
| Bun-first new project | Elysia | Fastest Bun framework with typing, docs, and client built in |
| Public REST API + internal typed client | ts-rest | Contract is the docs; OpenAPI export keeps external consumers happy |
| Existing Express/NestJS backend | ts-rest | Adapters drop into your current server without a rewrite |
| Realtime app needing subscriptions | tRPC or Elysia | Both have first-class streaming; tRPC has the more mature WS ecosystem |
| Team migrating from REST/OpenAPI | ts-rest | Keep your REST mental model; add types and validation gradually |

## tRPC — Move Fast and Break Nothing

**Repository**: [trpc/trpc](https://github.com/trpc/trpc) — 40,564 stars, last updated August 31, 2026.

tRPC's bet is radical: no schema files, no code generation, no REST routes to maintain — just TypeScript procedures on the server and a proxy client that calls them with full type inference. Define a router once, and your client knows every input and output shape at compile time.

**Server:**

```ts
// server/router.ts
import { initTRPC } from '@trpc/server';
import { z } from 'zod';

const t = initTRPC.create();

export const appRouter = t.router({
  greet: t.procedure
    .input(z.object({ name: z.string().min(1) }))
    .query(({ input }) => `Hello, ${input.name}!`),

  createTodo: t.procedure
    .input(z.object({
      title: z.string(),
      done: z.boolean().default(false),
    }))
    .mutation(({ input }) => {
      // persist to your database, then return
      return { id: 42, ...input };
    }),
});

export type AppRouter = typeof appRouter;
```

**Client — full inference, zero codegen:**

```ts
// client.ts
import { createTRPCProxyClient, httpBatchLink } from '@trpc/client';
import type { AppRouter } from './server/router';

const client = createTRPCProxyClient<AppRouter>({
  links: [httpBatchLink({ url: 'http://localhost:3000/trpc' })],
});

const greeting = await client.greet.query({ name: 'Ada' });
//            ^? string — typed, no .ts generated anywhere

const todo = await client.createTodo.mutate({ title: 'Ship it' });
// ^? { id: number; title: string; done: boolean }
```

Add an adapter (`@trpc/server/adapters/express` or `next`) and mount the router in about ten lines. `httpBatchLink` even batches concurrent calls into a single HTTP request. **Where it shines:** developer velocity is unmatched — rename a field in your router and every call site updates. **Where it hurts:** the RPC model leaks into your API design; if you need a public REST surface for third parties, you are adding a second layer rather than exposing one API.

## Elysia — The Bun-Native All-in-One

**Repository**: [elysiajs/elysia](https://github.com/elysiajs/elysia) — 19,039 stars, last updated August 30, 2026.

Elysia is a web framework "supercharged by Bun" with end-to-end type safety as a core feature, not an add-on. Server routes, runtime validation, OpenAPI documentation, and the typed client are all derived from a single source: your route definitions. Its benchmark claims (18x faster than Express on the TechEmpower suite) come from Bun's performance plus a heavily optimized runtime.

```ts
// server.ts
import { Elysia, t } from 'elysia';

const app = new Elysia()
  .get('/', () => 'Hello Elysia')
  .post('/todos', ({ body }) => ({ id: 1, ...body }), {
    body: t.Object({
      title: t.String(),
      done: t.Optional(t.Boolean()),
    }),
    detail: { summary: 'Create a todo' },
  })
  .listen(3000);

export type App = typeof app;
```

**Client — Eden Treaty:**

```ts
// client.ts
import { edenTreaty } from '@elysiajs/eden';
import type { App } from './server';

const api = edenTreaty<App>('http://localhost:3000');

const { data, error } = await api.todos.post({
  title: 'Buy milk',          // validated at compile time
  // done: 'not-a-boolean'    // <-- type error before you run it
});
```

Run the server with `bun run server.ts` and you get validation, typed routes, and — via `app.toOpenAPI()` — a spec document for tools like Swagger UI, all from one file. **Where it shines:** the tightest integration of the three — framework, validation, docs, and client compose without any glue code, and Bun's startup time makes it feel instant. **Where it hurts:** Elysia is the least boring choice — its TypeScript type gymnastics can confuse beginners, and going Node-native (instead of Bun) costs some ergonomics and performance.

## ts-rest — Contract-First, REST-Pure

**Repository**: [ts-rest/ts-rest](https://github.com/ts-rest/ts-rest) — 3,336 stars, last updated February 6, 2026.

ts-rest keeps REST semantics intact. You define a **contract** — routes, methods, request/response schemas — once, then reuse it on the server (validating every request) and on the client (typing every call). Unlike tRPC, there is no RPC layer to learn and no hidden wire format; your API is a normal REST API that OpenAPI tools and non-TypeScript clients can consume.

```ts
// contract.ts
import { initContract } from '@ts-rest/core';
import { z } from 'zod';

const c = initContract();

export const contract = c.router({
  createTodo: {
    method: 'POST',
    path: '/todos',
    body: z.object({ title: z.string(), done: z.boolean().default(false) }),
    responses: {
      201: z.object({ id: z.number(), title: z.string(), done: z.boolean() }),
      400: z.object({ message: z.string() }),
    },
  },
});
```

**Server (Express adapter) and client:**

```ts
// server.ts
import { createExpressEndpoints, initServer } from '@ts-rest/express';
import { contract } from './contract';

const s = initServer();
const router = s.router(contract, {
  createTodo: async ({ body }) => ({
    status: 201 as const,
    body: { id: 1, ...body },
  }),
});
createExpressEndpoints(contract, router, app);

// client.ts
import { initClient } from '@ts-rest/core';
const client = initClient(contract, { baseUrl: 'http://localhost:3000' });
const res = await client.createTodo({ body: { title: 'Groceries' } });
// res.status is 201 | 400, res.body is fully typed per status
```

Because the contract is a plain object, you can export it to OpenAPI (`@ts-rest/open-api`) or generate server stubs for other languages. **Where it shines:** it fits existing REST ecosystems — your API stays public, versioned, and toolable, while your TypeScript teams get type safety. **Where it hurts:** the contract adds a layer of ceremony tRPC and Elysia avoid; every endpoint must be described before it exists, and the smaller community means fewer battle-tested examples.

## Pitfalls and Migration Notes

1. **Do not mix RPC and REST casually.** If you choose tRPC, internal services and mobile clients should talk to the same router via adapters; exposing raw tRPC procedures to external consumers is an anti-pattern. For genuinely public APIs, start with ts-rest instead.
2. **Zod versions must match across the stack.** tRPC and ts-rest both lean on Zod; a version mismatch between server and client schemas produces subtle validation drift. Pin Zod in a shared workspace package.
3. **Monorepos are nearly mandatory for ts-rest** — the contract lives in a shared package imported by both sides. If your repo layout cannot host a shared package, tRPC or Elysia (which infer types from the server code) are simpler fits.
4. **Error handling differs from REST conventions.** tRPC throws typed errors that map to HTTP codes via `TRPCError`; Elysia uses `error` hooks and `t.Union` error models. Teams coming from REST must learn a new error vocabulary or standardize it early.
5. **TypeScript strictness is non-negotiable.** All three libraries rely on precise inference — `strict: true` and a modern `moduleResolution` are prerequisites. Running them on a legacy `tsconfig` silently degrades the type safety you are paying for.
6. **Plan the browser/runtime story.** tRPC supports React Server Components and edge runtimes via adapters; Elysia is Bun-first but runs on Node through an adapter; ts-rest is transport-agnostic. Decide your deployment target before committing.

## Why Type-Safe APIs Matter More in 2026

API drift is the most expensive bug class in web development: it is invisible to unit tests (both sides pass in isolation), undetectable by linters, and surfaces only when real users hit the missing field. Studies of production incidents consistently rank contract mismatches among the top causes of service degradation. The tools above do not just save typing — they move an entire failure class from runtime to compile time, where it costs seconds instead of incidents.

The ecosystem is converging on the same insight from different directions. gRPC teams have their own answer with typed protobuf contracts — see our [gRPC gateway vs Connect vs gRPC-Web comparison](../2026-04-24-grpc-gateway-vs-connect-vs-grpc-web-self-hosted-rest-proxy-guide-2026/) and the wider [RPC framework landscape](../2026-06-20-rpc-frameworks-grpc-twirp-connect-dubbo/) — while the TypeScript world solves it with inference and shared contracts. Whichever side you pick, the destination is the same: one definition of truth, enforced everywhere. And if you pair your API layer with a proper validation library like those covered in our [Zod vs Valibot vs Yup guide](../2026-08-12-zod-vs-valibot-vs-yup-typescript-schema-validation-comparison/), the boundary between frontend and backend stops being a type-safety hole entirely.

## FAQ

**Do I need a monorepo to use tRPC or Elysia?**
Not strictly. tRPC and Elysia infer types from the server, so a simple workspace or even a git submodule works — but a shared TypeScript project (pnpm/npm workspaces) makes the experience smooth. ts-rest genuinely wants a shared package for the contract.

**Can tRPC serve a public REST API for mobile apps or third parties?**
Yes, with effort: `trpc-openapi` generates OpenAPI specs from your router, and you can expose individual procedures as REST endpoints. But if a public REST surface is a primary requirement, ts-rest or a plain framework is less friction.

**Is Elysia tied to Bun?**
Elysia is designed for Bun — that is where its performance and ergonomics shine — but it runs on Node.js through an adapter. Bun 1.x+ is stable for production workloads, so the constraint is more about your infrastructure comfort than feasibility.

**How does validation failure behave in each tool?**
tRPC returns a `TRPCError` with `code: 'BAD_REQUEST'` (HTTP 400) for Zod failures. Elysia validates with TypeBox and returns 422 with a typed error body. ts-rest validates against the contract and returns 400 with the Zod issue list. All three are configurable.

**Which one has the best OpenAPI story?**
Elysia produces OpenAPI from route definitions with minimal annotations (`detail` per route) and even serves Swagger UI via a plugin. ts-rest exports from the contract with `@ts-rest/open-api`. tRPC requires `trpc-openapi` and works best for simpler procedures. For doc-first teams, ts-rest and Elysia lead.

**Can I migrate an existing Express API without rewriting it?**
With ts-rest, yes — you wrap existing handlers with `initServer` and the contract, migrating endpoint by endpoint while the API surface stays identical. With tRPC or Elysia you are effectively building a new API layer, so plan a coexistence window with a reverse proxy splitting traffic.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "tRPC vs Elysia vs ts-rest in 2026: End-to-End Type-Safe TypeScript APIs Compared",
  "description": "Compare tRPC, Elysia, and ts-rest for end-to-end type-safe TypeScript APIs — RPC, framework, and contract-first approaches with real code, decision matrices, and migration guidance for 2026.",
  "datePublished": "2026-09-01",
  "dateModified": "2026-09-01",
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
