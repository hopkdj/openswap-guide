---
title: "Orval vs Kubb vs openapi-typescript in 2026: The Best TypeScript API Client Generator"
date: "2026-10-01"
tags: ["typescript", "openapi", "code-generation", "api", "developer-tools"]
draft: false
cover: "/img/screenshots/orval-banner.jpg"
---

Hand-written fetch wrappers rot the moment your backend ships a new field. You rename one property in the OpenAPI spec, forget to update three call sites, and the bug surfaces in production as `undefined` in a payment form. Type generation is supposed to fix that — but the tools solve the problem in genuinely different ways, and picking the wrong one means either 40 MB of generated code or a client that still lets you pass `any`.

**Orval, Kubb and openapi-typescript** are the three serious options in 2026. All three are MIT-licensed and actively maintained, but they sit at different points on the "runtime-free types vs batteries-included generator" spectrum. Here is what that difference costs you.

![Orval branded banner](/img/screenshots/orval-banner.jpg "Orval generates type-safe TypeScript clients from any OpenAPI or Swagger specification")

## Quick Verdict

**Use openapi-typescript + openapi-fetch** if you want a **6 KB runtime**, zero code generation magic, and types that compile away entirely — best for teams that already control their own fetch layer. **Use Orval** if you want one config file that emits clients, hooks, mocks and schemas together, with per-operation overrides. **Use Kubb** if you want a plugin engine where the output is composed from discrete plugins (types, fetch, axios, Zod, MSW, React Query) and generation can run inside your bundler. In one line: **openapi-typescript for minimalism, Orval for batteries-included, Kubb for composability.**

## Head-to-Head Comparison

Live GitHub and npm data pulled on 2026-10-01:

| Dimension | openapi-typescript | Orval | Kubb |
|---|---|---|---|
| GitHub stars | 8,387 | 6,491 | 1,812 |
| Latest version | 7.13.0 (types), 0.17.0 (openapi-fetch) | 8.39.0 | 5.4.1 |
| License | MIT | MIT | MIT |
| Core idea | Runtime-free TS types from OpenAPI 3.0/3.1 | Config-driven generator for clients, hooks, mocks | Plugin-based meta framework for codegen |
| Runtime cost | ~6 KB client (`openapi-fetch`) | Generated client uses your chosen HTTP library | Plugin-dependent (fetch, axios, etc.) |
| Output | `.d.ts` types + tiny typed client | Typed endpoints, models, mocks, per-operation overrides | Types, clients, hooks, validators, mocks, handlers |
| Plugin / extension model | Companion packages (`openapi-react-query`, `openapi-fetch`) | Config options + custom mutators and transformers | Explicit plugin list, swappable adapters and renderers |
| Zod / validation | No | Via generated schemas and custom config | First-class `plugin-zod` |
| Mock generation | No | Yes (`mock: true`, Faker integration) | Yes (`plugin-faker`, `plugin-msw`) |
| Bundler integration | CLI in package scripts | CLI / Docker image | `unplugin-kubb` for Vite, Nuxt, Astro, webpack |
| Best for | Teams that want types only | Full client generation in one config | Composable, plugin-assembled pipelines |

## Decision Matrix: Pick in 10 Seconds

| Your situation | Pick | Why |
|---|---|---|
| You already have a fetch wrapper you like | **openapi-typescript** | Generate types, keep your transport, add ~6 KB only |
| You need TanStack Query hooks generated, not hand-written | **Orval** | Query hooks and mocks are first-class output targets |
| You want Zod validators alongside types from one schema | **Kubb** | `plugin-zod` is a plugin, not a separate pipeline |
| Your CI already runs Dockerized generators | **Orval** | Official container image is published for CI use |
| You want generation to run inside Vite/Nuxt/Astro builds | **Kubb** | `unplugin-kubb` integrates with the bundler |
| You only need `paths` and `components` types | **openapi-typescript** | That is literally the whole product |
| You want per-operation overrides and custom mutators | **Orval** | `override.operations` is built into the config |
| You are replacing an old codegen with a plugin model | **Kubb** | The plugin list is explicit and auditable |

## openapi-typescript — Types With No Runtime

openapi-typescript takes the opposite approach to a classic generator: it emits **types only** and nothing else. The output compiles to nothing, so there is no runtime dependency, no generated class hierarchy, and no wrapper you have to debug. Version **7.13.0** supports OpenAPI 3.0 and 3.1, including discriminators, and can pull a schema from a local file or a URL.

Setup is two packages and a compiler hint, straight from the project's README:

```bash
npm i -D openapi-typescript typescript
npx openapi-typescript ./path/to/my/schema.yaml -o ./path/to/my/schema.d.ts
```

The README also recommends two tsconfig settings that materially improve safety — `moduleResolution: "Bundler"` (or `NodeNext`) so the generated types load correctly, and `noUncheckedIndexedAccess` for stricter index access. Then you pair the types with the companion client, which is the part that keeps the bundle tiny:

```ts
import createClient from "openapi-fetch";
import type { paths } from "./my-openapi-3-schema"; // generated by openapi-typescript

const client = createClient<paths>({ baseUrl: "https://myapi.dev/v1/" });

const { data, error } = await client.GET("/blogposts/{post_id}", {
  params: { path: { post_id: "123" } },
});
```

The important detail is that `data` and `error` are inferred, not asserted. Path parameters, query strings and request bodies all typecheck against the schema, so a typo in a URL or a missing required body field is a compile error rather than a 400 at runtime. This is the "no generics, no manual typing" promise in the project's own documentation — and at **8,387 stars** it is the most popular of the three precisely because the result is so small.

The trade-off is honest: you get types and a thin fetch wrapper, and nothing else. No hooks, no mocks, no validators. If you need those, you either add the companion `openapi-react-query` package or move to one of the config-driven generators.

## Orval — One Config, Full Client Generation

Orval is the "just make it work" option. Point one config file at your spec and it emits typed endpoints, model schemas, and optionally mock handlers. At **6,491 stars** and version **8.39.0**, it has the largest set of output targets among the three and the most granular control per operation.

Here is a real configuration file taken from the project's own samples — note `mock: true` and the per-operation `override` block, which are the two features people pick Orval for:

```ts
import { defineConfig } from 'orval';

export default defineConfig({
  'petstore-file': {
    input: './petstore.yaml',
    output: {
      target: './api/endpoints/petstoreFromFileSpecWithConfig.ts',
      formatter: 'prettier',
    },
  },
  'petstore-file-transformer': {
    output: {
      target: './api/endpoints/petstoreFromFileSpecWithTransformer.ts',
      schemas: './api/model',
      formatter: 'prettier',
      mock: true,
      override: {
        operations: {
          listPets: {
            mutator: './api/mutator/response-type.ts',
          },
        },
      },
    },
  },
});
```

Two operational advantages stand out for team use. First, the project publishes an official container image (`ghcr.io/orval-labs/orval`), which means you can run generation in CI without pinning a Node toolchain — genuinely useful when the generator is one step in a larger pipeline. Second, `override.operations` lets you swap the response type or the transport for a single endpoint without forking the generator, which is exactly the escape hatch you need when one legacy endpoint returns something the spec does not describe.

Orval's cost is generated surface area. Because it can emit models, endpoints, mocks and hooks together, a large spec produces a large `api/` directory that you must review and commit. Teams that skip that review end up with thousands of lines of generated diffs in every schema-changing pull request.

![Kubb logo](/img/screenshots/kubb-logo.jpg "Kubb is a plugin-based code generation framework for OpenAPI schemas")

## Kubb — Codegen as a Plugin Engine

Kubb is the youngest and smallest of the three at **1,812 stars**, but it has the cleanest mental model: it is a **meta framework for code generation** where every output is produced by a plugin you explicitly enable. Version **5.4.1** reads OpenAPI 2.0, 3.0 and 3.1 through adapters such as `@kubb/adapter-oas`.

Getting started is wizard-driven, which is unusual for a codegen tool and pleasant in practice:

```bash
bun add kubb
npx kubb init      # creates kubb.config.ts, guides plugin selection, installs packages
npx kubb generate  # runs generation
```

The plugin catalogue is the reason to choose Kubb: `plugin-ts`, `plugin-axios`, `plugin-fetch`, `plugin-react-query`, `plugin-vue-query`, `plugin-swr`, `plugin-zod`, `plugin-faker`, `plugin-msw`, `plugin-cypress`, `plugin-redoc` and `plugin-mcp` are all separate packages. Nothing is generated that you did not ask for. The wizard writes a config with an `input`, an `output` and an explicit `plugins` array, and you extend it from there:

```ts
export default defineConfig({
  input: { path: './petStore.yaml' },
  output: { path: './src/gen' },
  plugins: [pluginTs(), pluginFetch(), pluginZod(), pluginReactQuery()],
});
```

Because the plugin list is explicit, code review of a schema change becomes review of a diff you can reason about: add `plugin-zod` and the reviewer knows validation schemas appeared. Kubb also integrates with build tooling through `unplugin-kubb`, so generation can run as part of a Vite, Nuxt, Astro or webpack build instead of as a separate script that someone forgets to run. If you want to inspect generation visually, the project offers a browser-based companion for configuring and diffing runs, while the core stays MIT-licensed and works without it.

The trade-off is ecosystem size: fewer stars, fewer Stack Overflow answers, and a plugin boundary you must respect. Reach for Kubb when you want a composable pipeline, not when you want the most search results.

## Pitfalls and Migration Notes

**Generated types are not validation.** openapi-typescript gives you compile-time safety only — a malformed response at runtime still passes through. If you need to validate untrusted payloads, generate Zod schemas (Kubb's `plugin-zod`) or add a runtime validator yourself.

**Speccing correctly matters more than the tool.** All three generators are only as good as your `operationId`s, response schemas and discriminated unions. A spec full of `additionalProperties: true` produces `unknown` everywhere and no safety at all.

**Do not commit generated output without a diff policy.** Orval and Kubb can both produce large diffs on a schema change. Decide up front whether generated code is committed (reviewable, noisy) or built in CI (clean history, slower builds).

**Pin your generator version in CI.** A floating generator version turns an unrelated dependency bump into a thousand-line diff. Pin `orval`, `kubb` or `openapi-typescript` exactly, and upgrade deliberately.

**Watch the tsconfig.** openapi-typescript's own documentation is explicit that `moduleResolution` and `noUncheckedIndexedAccess` affect whether the generated types behave correctly. Skipping those settings produces confusing "type not found" errors.

If you are working in the JavaScript/TypeScript API layer more broadly, our [tRPC vs Elysia vs ts-rest comparison](../2026-09-01-trpc-vs-elysia-vs-ts-rest-typesafe-apis-comparison/) covers the RPC-first approach, the [Node.js HTTP framework comparison](../2026-07-28-nodejs-http-frameworks-express-koa-fastify-hono-comparison/) covers the server side, and the [code generation guide](../2026-04-30-openapi-generator-vs-swagger-codegen-vs-jhipster-self-hosted-code-generation-guide-2026/) covers the older JVM generation stack for contrast.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Orval vs Kubb vs openapi-typescript in 2026: The Best TypeScript API Client Generator",
  "description": "Comparison of Orval 8, Kubb 5 and openapi-typescript 7 for generating type-safe TypeScript API clients from OpenAPI specs, with real config examples and selection criteria.",
  "datePublished": "2026-10-01",
  "dateModified": "2026-10-01",
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

**Which generator produces the smallest JavaScript bundle?**
openapi-typescript. The generated output is types only, and the companion `openapi-fetch` client is roughly 6 KB, so almost nothing ships to the browser compared with a generated client from a full-featured generator.

**Can these tools generate TanStack Query hooks automatically?**
Yes. Orval generates query hooks as a configured output target, and Kubb does it through `plugin-react-query`, `plugin-vue-query` or `plugin-swr` depending on your framework.

**Do I need a running API server to generate clients?**
No. All three tools read the OpenAPI document itself, from a local YAML or JSON file or from a URL. openapi-typescript's documentation makes a point of this: no Java, no node-gyp, no live server required.

**Which one should a team new to OpenAPI codegen start with?**
Start with openapi-typescript plus openapi-fetch. It is the smallest change to an existing codebase, and it teaches you immediately whether your spec is good enough for generation to help. Move to Orval or Kubb when you specifically need hooks, mocks or validators.

**Is committed generated code a bad practice?**
Not inherently. Committing generated clients makes diffs reviewable and builds reproducible; generating in CI keeps history clean but hides output changes. The failure mode is committing without reviewing, not committing itself.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
