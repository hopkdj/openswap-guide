---
title: "Zod vs Valibot vs Yup in 2026: Which TypeScript Schema Library Should You Actually Use?"
date: "2026-08-12"
tags: ["typescript", "validation", "schema", "zod", "valibot", "developer-tools"]
draft: false
cover: "/img/screenshots/valibot-docs.jpg"
---

You ship a new API endpoint, the client sends a request body, and the first thing your code does is pray that `email` is actually an email. Every TypeScript project eventually hits the same wall: TypeScript types vanish at runtime, so the data arriving at your server, your form, or your database adapter is untrusted until proven otherwise. Runtime schema validation is the industry answer, but the three dominant libraries — **Zod (43,450 stars), Yup (23,673 stars), and Valibot (8,926 stars)** — take radically different approaches to the same problem. Pick wrong and you are stuck with a dependency that bloats your bundle, slows your type checking, or fights your framework's conventions for years.

This comparison is based on live GitHub data pulled in August 2026, official documentation, and real bundle-size measurements. No vendor marketing, just what each library actually does under load.

## TL;DR: Quick Verdict

- **Choose Zod** if you want the community standard with the best documentation, the largest ecosystem of integrations, and you do not care about a ~50 kB runtime cost. It is the safest default for almost every project.
- **Choose Valibot** if bundle size matters — API routes, edge functions, mobile web, or anything where every kilobyte counts. Its modular design can cut validation payloads by up to 95% compared to Zod.
- **Choose Yup** if you are maintaining an existing form-heavy React or Node.js codebase that already uses it, or you need its mature transformation and conditional-validation features. Do not start a greenfield TypeScript API with it — its type inference lags behind the other two.

## The Contenders at a Glance

| Dimension | Zod | Valibot | Yup |
|---|---|---|---|
| **GitHub stars** | 43,450 | 8,926 | 23,673 |
| **Last push** | 2026-08-11 | 2026-08-11 | 2026-08-12 |
| **License** | MIT | MIT | MIT |
| **Bundle size (core)** | ~50 kB minified | from ~700 bytes (tree-shaken) | ~35 kB minified |
| **Runtime dependencies** | 0 | 0 | 1 (`property-expr`) |
| **Type inference** | `z.infer` — excellent | `v.InferOutput` — excellent | `InferType` — good but lossy on transforms |
| **Tree-shaking** | Limited | First-class (function-per-action design) | Limited |
| **Style** | Chainable methods | Composable functions + pipes | Chainable methods, Promise-native |
| **Framework integrations** | tRPC, react-hook-form, TanStack Form, NestJS | tRPC, react-hook-form, TanStack Form, more every month | Formik, react-hook-form, many legacy tools |
| **Learning curve** | Shallow | Shallow (modular, explicit) | Shallow |
| **Best for** | General-purpose TS apps, APIs, full-stack frameworks | Bundle-sensitive edge/serverless code | Legacy form-heavy React apps |

## Decision Matrix

| Use Case | Recommended Tool | Reason |
|---|---|---|
| New full-stack TypeScript app (API + client) | **Zod** | Best docs, `z.infer` everywhere, tRPC and TanStack integrations out of the box |
| Edge function / serverless route validation | **Valibot** | Sub-kilobyte core; pay only for the validators you import |
| Public library or SDK published to npm | **Valibot** | Consumers inherit your tiny dependency footprint |
| Existing React + Formik/Yup codebase | **Yup** | Migrating schema logic is more work than keeping it; Yup's `validate` is battle-tested |
| Mobile web or large enterprise SPA with strict bundle budgets | **Valibot** | Up to 95% smaller validation payload than Zod |
| Data pipeline / ETL where schemas transform values | **Yup** | `transform`, `default`, and conditional logic are mature |
| Team already fluent in Zod patterns | **Zod** | Consistency beats marginal bundle savings for most teams |

## Zod: The TypeScript-First Standard

Zod's pitch is simple: define a schema once, and it serves as both your runtime validator and your TypeScript type source. The `z.infer` helper removes the classic "write a type, write a validator, keep them in sync" boilerplate that plagued the ecosystem before it.

```ts
import * as z from "zod";

const User = z.object({
  name: z.string(),
  age: z.number().int().min(0),
  email: z.string().email(),
});

// some untrusted data...
const input = { name: "jane", age: 29, email: "jane@example.com" };

// the parsed result is validated and type safe!
const parsed = User.parse(input);
```

With **43,450 stars** and commits landing as recently as August 2026, Zod is the de facto standard. It powers tRPC's input validation, react-hook-form resolvers, TanStack Form adapters, NestJS pipes, and dozens of other integrations. Its error messages are readable by default, and `safeParse` returns a discriminated union (`{ success: true, data } | { success: false, error }`) that makes handling failures in server code genuinely pleasant.

The cost is size. A full Zod import lands around **50 kB minified**, and because the library exposes a chainable object API, tree-shakers cannot reliably eliminate the methods you never call. In a world where edge functions charge per millisecond and per byte, that weight is the reason Valibot exists. Zod also relies on TypeScript's type system heavily — `z.infer` on complex recursive schemas can slow down type checking in very large codebases, though the Zod team has steadily improved this.

## Valibot: The Tree-Shakable Minimalist

Valibot was created in 2023 by Fabian Hiller to answer one question: why should validating a login form cost your users 50 kB of JavaScript? Its core insight is modularity — instead of one large object with dozens of chainable methods, Valibot exports hundreds of tiny, independent functions (`v.string`, `v.email`, `v.minLength`, `v.pipe`, ...). Bundlers can then drop every function you do not import.

```ts
import * as v from 'valibot'; // 1.31 kB

// Create login schema with email and password
const LoginSchema = v.object({
  email: v.pipe(v.string(), v.email()),
  password: v.pipe(v.string(), v.minLength(8)),
});

// Infer output TypeScript type of login schema as
// { email: string; password: string }
type LoginData = v.InferOutput<typeof LoginSchema>;

// Throws error for email and password
const output1 = v.parse(LoginSchema, { email: '', password: '' });

// Returns data as { email: string; password: string }
const output2 = v.parse(LoginSchema, {
  email: 'jane@example.com',
  password: '12345678',
});
```

The bundle math is the headline: a minimal Valibot schema costs **less than 700 bytes** after tree-shaking, and the maintainers claim up to **95% reduction** compared to an equivalent Zod setup. At **8,926 stars** it is younger and smaller than its rivals, but it is actively maintained (last push August 2026), 100% dependency-free, and has been adopted by tRPC, react-hook-form, and a growing list of frameworks.

The trade-offs: its API is more verbose than Zod's for nested schemas (explicit `pipe` calls everywhere), the ecosystem of community tutorials is thinner, and its rapid release cadence means occasional breaking changes between minor versions — pin your dependency and read the changelog before upgrading. For serverless and edge deployments where cold-start time and payload size directly hit your bill, the trade is almost always worth it.

## Yup: The Mature Form Veteran

Yup has been validating JavaScript objects since 2018, long before the TypeScript-first wave. It is built on a Promise-native API with a fluent, chainable style that made it the default companion to Formik — the most popular React form library of the last generation.

```ts
import * as yup from 'yup';

let schema = yup.object().shape({
  name: yup.string(),
  age: yup.number().min(18),
});

try {
  await schema.validate({ name: 'jimmy', age: 11 });
} catch (err) {
  console.log(err.errors); // ["age must be greater than or equal to 18"]
}
```

With **23,673 stars** and an active August 2026 release, Yup is far from abandoned. Its genuine strengths: first-class `transform`, `default`, and `when` (conditional) APIs, mature `cast` behavior for coercing input, and a validation model that is fully async and works naturally inside form libraries. For data pipelines that need to normalize input while validating it, Yup's transform chain is still the most ergonomic of the three.

The weaknesses are the reason we do not recommend it for new projects. Its TypeScript inference (`InferType`) loses precision around transforms and defaults — you frequently need explicit type annotations where Zod and Valibot infer correctly. It carries a runtime dependency (`property-expr`) and a larger base bundle (~35 kB). And the API surface, while familiar to veterans, mixes validation, coercion, and defaults in ways that surprise newcomers. If you are starting fresh in 2026, the other two are better investments; if you maintain a Formik codebase, Yup remains a perfectly reasonable choice.

## Migration and Coexistence Strategies

Moving between these libraries is a mechanical, schema-by-schema process — but there are real traps.

**From Yup to Zod or Valibot.** The mapping is mostly direct: `yup.string().required()` → `z.string().min(1)` or `v.pipe(v.string(), v.minLength(1))`; `yup.number().min(18)` → `z.number().min(18)`. The tricky part is Yup's `transform` and `cast` behavior, which has no direct Zod equivalent — you need `z.preprocess` or `z.coerce`, and in Valibot, explicit `v.transform` steps inside `v.pipe`. Budget extra time for every schema that used defaults or coercion.

**From Zod to Valibot.** This is the easiest migration because Valibot's action functions map 1:1 to Zod methods (`z.email()` → `v.email()`, `z.min(5)` → `v.minValue(5)`). The `pipe` syntax forces you to write the order of checks explicitly, which is a good thing — it eliminates Zod's occasional ambiguity about whether `z.string().email().min(5)` validates length before or after format.

**Coexistence in a monorepo.** You do not need a big-bang migration. Valibot and Zod can share a package boundary cleanly: keep Zod in the legacy app, introduce Valibot in new service packages, and translate at the API edge with a small adapter function. The one thing to avoid is mixing both libraries inside a single schema — the inferred types are structurally compatible but debugging two validation error formats in one trace is miserable.

**CI and type-checking cost.** Large monorepos report that replacing Zod with Valibot noticeably speeds up `tsc` on schema-heavy packages, because Valibot's function-per-action design produces simpler inferred types. If your CI type-check step is a bottleneck, benchmark both on your worst schema file before committing.

## Common Pitfalls and Performance Traps

1. **`parse` in hot paths.** `z.parse`, `v.parse`, and `yup.validate` all throw on failure. If you validate the same object in a loop (per-row ETL, request middleware), the throw/catch overhead adds up. Use `safeParse` / `safeValidate` and collect errors instead.
2. **Recursive schemas blow up type checking.** Self-referencing schemas (trees, graphs) require the `z.lazy` / `v.recursive` escape hatch. Writing them without it produces circular type errors that are confusing to debug.
3. **`email` is not an RFC validator.** All three libraries use pragmatic regexes for email, not full RFC 5322 parsing. They reject technically-valid addresses like `user+tag@example.com` variants depending on version — know your acceptance criteria.
4. **Number precision.** `z.number()` accepts `NaN` and `Infinity` by default; `yup.number()` rejects them. If you validate API payloads, add `.finite()` (Zod) or `v.finite()` (Valibot) explicitly or you will ship NaN to your database.
5. **Bundle bloat from barrel imports.** With Zod, importing from the root package pulls everything. With Valibot, importing from the root is fine — tree-shaking works — but only if you use a bundler that actually tree-shakes (Vite, webpack 5+, esbuild). Transpiling with `tsc` alone does not shake anything.
6. **Version drift in adapters.** react-hook-form resolvers and tRPC sometimes lag the latest library versions. If you upgrade Zod or Valibot and your form resolver breaks, check the resolver package's peer dependency range before filing a bug report.

## FAQ

**What is the difference between Zod and Valibot?**
Both are TypeScript-first schema validation libraries with excellent type inference. The difference is architecture: Zod uses a monolithic chainable API (~50 kB), while Valibot is modular with hundreds of tiny functions that tree-shake down to under 700 bytes for simple schemas.

**Is Yup still maintained in 2026?**
Yes. Yup's repository received commits in August 2026 and it has 23,673 stars. It remains a solid choice for existing Formik-based React applications, but its TypeScript inference is less precise than Zod's or Valibot's for new projects.

**Can I use Zod with Valibot in the same project?**
You can, but avoid mixing them inside a single schema. The inferred types are structurally compatible, but error formats differ. A common pattern is keeping Zod in a legacy app and adopting Valibot for new packages, translating at the API boundary.

**Which library has the smallest bundle size?**
Valibot, by a wide margin. A minimal schema costs less than 700 bytes after tree-shaking versus roughly 50 kB for Zod. Valibot's maintainers document up to 95% bundle reduction compared to equivalent Zod usage.

**Does Valibot work with react-hook-form and tRPC?**
Yes. Valibot ships official resolvers for react-hook-form and is a first-class validation option in tRPC, alongside Zod. Adoption is growing quickly across the TypeScript ecosystem.

**Which schema library should I use for an edge function?**
Valibot. Edge runtimes charge for compute time and payload transfer, and Valibot's tiny, tree-shaken output directly reduces both. For the same reason it is the best choice for public npm packages consumed by other developers.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Zod vs Valibot vs Yup in 2026: Which TypeScript Schema Library Should You Actually Use?",
  "description": "Deep comparison of the three dominant TypeScript schema validation libraries: Zod, Valibot, and Yup. Bundle sizes, type inference, GitHub stats, migration strategies, and a decision matrix for 2026.",
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

For more TypeScript validation coverage, see our comparison of [TypeBox vs ArkType vs Runtypes](../2026-07-24-typescript-schema-validation-typebox-arktype-runtypes/) and the older [JSON Schema validation tools AJV vs Prism vs Joi](../2026-06-08-self-hosted-json-schema-validation-ajv-prism-joi/). If you are wiring validation into dependency injection, our [TypeScript DI containers guide](../2026-07-21-typescript-di-containers-tsyringe-inversifyjs-typedi/) covers the other half of clean server architecture.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
