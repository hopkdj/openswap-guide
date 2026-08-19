---
title: "TypeScript Functional Programming in 2026: Effect vs fp-ts vs neverthrow — Which One Should You Actually Use?"
date: "2026-08-19"
tags: ["typescript", "functional-programming", "javascript", "effect", "developer-tools"]
draft: false
cover: "/img/screenshots/effect-cover.png"
---

Every TypeScript developer has felt it: a `fetch` that throws deep inside a promise chain, a `null` check you forgot at the wrong layer, and error handling code that reads like an archaeological dig across `try/catch` blocks. Functional programming libraries promise to fix this by making errors *values* instead of exceptions — but the choice is confusing. **Effect** (15,344 stars) is the rising framework claiming to replace half your stack, **fp-ts** (11,538 stars) is the algebraic toolbox that taught a generation of TypeScript devs about `Either` and `Option`, and **neverthrow** (7,675 stars) is the simple `Result` type that just wants to make your functions honest. They are not the same thing, and picking wrong means rewiring your entire codebase.

## TL;DR: Quick Verdict

- **Choose neverthrow** if you want one type (`Result<T, E>`) with a tiny API surface — no category theory required. It is the fastest path to eliminating thrown errors in an existing codebase.
- **Choose fp-ts** if you want the full algebraic toolbox (`Option`, `Either`, `Reader`, `State`, `TaskEither`) and you are comfortable composing with `pipe`. Be ready for version churn and a steep learning curve.
- **Choose Effect** if you are starting a new production service and want an all-in-one runtime: typed errors, dependency injection via `Layer`, structured concurrency, and observability — Effect is the most actively developed project of the three (last commit: today) and the safest long-term bet.

**For a brand-new service in 2026: Effect.** For a surgical fix in an existing codebase: neverthrow. fp-ts sits in the middle — powerful, but its ecosystem momentum is slowly draining toward Effect.

## Comparison at a Glance

| Feature | Effect | fp-ts | neverthrow |
|---|---|---|---|
| **Core abstraction** | `Effect<A, E, R>` — full effect runtime | Algebraic types (`Either`, `Option`, `TaskEither`) | `Result<T, E>` / `ResultAsync<T, E>` |
| **Stars** | 15,344 | 11,538 | 7,675 |
| **Last update** | Aug 19, 2026 (today) | Apr 2026 | Feb 2026 |
| **Learning curve** | Steep | Steep | Shallow |
| **Bundle impact** | Large but tree-shakeable | Moderate | Minimal |
| **Typed errors** | Yes, at the type level | Yes | Yes |
| **Concurrency model** | Structured (Fibers, interruption) | None (combinators only) | None |
| **Dependency injection** | Built-in (`Layer`, `Context`) | DIY via `Reader` | Not provided |
| **Observability / tracing** | Built-in (Effect + Otel) | Not provided | Not provided |
| **Testing story** | `TestClock`, `TestContext` | Manual | Manual |
| **Version stability** | v3.x, fast-moving | v3.x (post 2023 rewrite) | v8.x, very stable |
| **License** | MIT | MIT | MIT |

## Decision Matrix: Which Tool for Your Use Case?

| Use Case | Recommended Tool | Why |
|---|---|---|
| New microservice with config, DB, HTTP, and retries | **Effect** | `Config`, `Layer`, `Effect.tryPromise`, and structured concurrency replace 5 separate libraries |
| Legacy Express/Fastify app — just stop throwing | **neverthrow** | Drop-in `Result` return types; no runtime, no `pipe`, no fantasy-land |
| API boundary validation + typed errors | **neverthrow + zod** | `andThen` chains read like a spec; pair with [zod schema validation](../2026-08-12-zod-vs-valibot-vs-yup-typescript-schema-validation-comparison/) |
| Team already knows `Either`/`Option` style | **fp-ts** | If your team writes `pipe` fluently, fp-ts gives the toolbox without Effect's runtime opinions |
| Long-lived codebase, want architectural guarantees | **Effect** | The only option with a real runtime: interruption, supervision, retry policies, and DI built in |
| Library author targeting many TS consumers | **neverthrow** | Smallest surface and zero runtime assumptions — consumers can adopt it without learning FP |

## neverthrow: The Honest Result Type

neverthrow's entire pitch fits in one sentence: **functions should return results, not throw**. It gives you `Result<T, E>` with `ok()` and `err()` constructors, and a fluent chain API (`map`, `andThen`, `mapErr`, `match`) that works on both synchronous and async values via `ResultAsync`.

```shell
npm install neverthrow
```

```ts
import { ok, err, Result } from "neverthrow";

// A function that never throws — it returns a Result
const divide = (a: number, b: number): Result<number, string> =>
  b === 0 ? err("division by zero") : ok(a / b);

// Chain operations; the error type flows through
const result = divide(10, 2)
  .map((n) => n * 2)                      // ok(10)
  .andThen((n) => divide(n, 0))           // err("division by zero")

// Handle both cases at the end
result.match(
  (value) => console.log("OK:", value),
  (error) => console.error("FAIL:", error),
);
```

For async code, `ResultAsync` wraps promises:

```ts
import { okAsync, ResultAsync } from "neverthrow";

const fetchUser = (id: string): ResultAsync<User, ApiError> =>
  ResultAsync.fromPromise(
    fetch(`/users/${id}`).then((r) => r.json()),
    () => ({ kind: "network" as const }),
  );

const fullUser = fetchUser("42").andThen((user) =>
  user.plan ? fetchPlan(user.plan) : okAsync(user),
);
```

The genius is the restraint. There is no `pipe`, no typeclass hierarchy, no fantasy-land spec to learn — the chain methods are plain methods, TypeScript infers the error union across the whole chain, and you can introduce it file by file in an existing codebase.

![neverthrow Result chain demo](/img/screenshots/neverthrow-demo.png "neverthrow official demo: chaining Result and ResultAsync values with type-safe error handling")

**That is why neverthrow is the safest "first FP library" a team can adopt.** The trade-off: it solves *errors* and nothing else. No concurrency model, no dependency injection, no structured retries — once your codebase outgrows it, you migrate up.

## fp-ts: The Algebraic Toolbox

fp-ts is the library that made functional programming *respectable* in TypeScript. Created by Giulio Canti, it brings the Haskell/OCaml style — `Option`, `Either`, `Reader`, `State`, `IO`, `Task`, `TaskEither`, `NonEmptyArray`, and dozens of typeclass instances — all composed through a `pipe` function. If you have seen `pipe(x, map(f), chain(g))` in TypeScript, you have seen fp-ts.

```shell
npm install fp-ts
```

```ts
import { pipe } from "fp-ts/function";
import { left, right, map, chain, fold } from "fp-ts/Either";

const divide = (a: number, b: number): Either<string, number> =>
  b === 0 ? left("division by zero") : right(a / b);

const result = pipe(
  divide(10, 2),
  map((n) => n * 2),
  chain((n) => divide(n, 0)),
);

// Extract the value at the boundary
fold(
  (error) => console.error("FAIL:", error),
  (value) => console.log("OK:", value),
)(result);
```

The power is composition *across* structures: `Option` for missing values, `Either` for recoverable errors, `TaskEither` for async fallible work, `ReaderTaskEither` for async work that needs injected dependencies. You can build `validate → transform → persist` pipelines where every stage is explicit about what it can fail on. fp-ts was the default answer to "functional TypeScript" from 2019 to 2023.

**Why momentum shifted:** fp-ts v3 (2023) was a major breaking rewrite that fragmented the ecosystem — libraries like `io-ts` and `fp-ts-rxjs` lagged behind, and some were abandoned. Meanwhile Effect shipped its own complete platform (Effect v3, 2024+) that absorbed most of fp-ts's ideas but added what fp-ts deliberately omits: a runtime. Many former fp-ts maintainers and contributors now work on Effect's ecosystem. fp-ts is still excellent, still maintained, but **its trajectory in 2026 is "stable and shrinking" rather than "growing."**

## Effect: The Complete Runtime

Effect is not a library — it is a platform. The core type `Effect<A, E, R>` represents a program that succeeds with `A`, fails with `E`, and *requires* context `R`. Around that type, Effect provides typed errors, dependency injection with `Layer` and `Context`, structured concurrency with `Fiber` and interruption, retry/schedule policies, a `Stream` type for async iteration, `Schema` for runtime validation, and built-in OpenTelemetry tracing.

```shell
npm install effect@rc
```

```ts
import { Effect } from "effect";

// Typed failure: the error channel carries the exact error type
const divide = (a: number, b: number): Effect.Effect<number, string> =>
  b === 0 ? Effect.fail("division by zero") : Effect.succeed(a / b);

// Effect.gen gives you generator-based composition (like async/await, but for effects)
const program = Effect.gen(function* () {
  const n = yield* divide(10, 2);
  const doubled = n * 2;
  return yield* divide(doubled, 0); // fails with "division by zero"
});

// The boundary: run the effect in the real world
Effect.runPromise(program)
  .then((value) => console.log("OK:", value))
  .catch((error) => console.error("FAIL:", error));
```

What makes Effect genuinely different is the middle layer. Dependency injection is not a pattern you implement — it is `Context` and `Layer`:

```ts
import { Context, Effect, Layer } from "effect";

class Database extends Context.Tag("Database")<Database, { query: (sql: string) => Effect.Effect<unknown, Error> }>() {}

const DatabaseLive = Layer.effect(
  Database,
  Effect.succeed({ query: (sql) => Effect.succeed({ rows: [] }) }),
);

const program = Effect.gen(function* () {
  const db = yield* Database;
  return yield* db.query("SELECT 1");
});

const runnable = Effect.provide(program, DatabaseLive);
Effect.runPromise(runnable);
```

Retries and timeouts are policies, not try/catch loops:

```ts
import { Effect, Schedule } from "effect";

const fetchWithRetry = Effect.retry(
  fetchData,
  Schedule.exponential("100 millis", 2).pipe(Schedule.recurs(5)),
);
```

Structured concurrency means fibers are supervised and interrupted automatically when their parent completes or fails — no leaked timers, no unhandled promise rejections. This is a *runtime* guarantee, the kind of thing neither fp-ts nor neverthrow can offer because they deliberately have no runtime.

The cost: **learning curve.** Effect has its own vocabulary (`Effect`, `Layer`, `Fiber`, `Schedule`, `Scope`, `Ref`, `Stream`, `Channel`), its own eslint plugin, and code that can take months to read fluently. Bundle size is larger (tree-shaking helps, but the runtime is real). For a 500-line utility, Effect is absurd; for a production service with config, database, HTTP, background jobs, and telemetry, it collapses what would otherwise be five libraries into one coherent model — and its active development pace (commits this week) means the answer to "is Effect the future?" is trending hard toward yes.

## Common Pitfalls and Migration Notes

**1. Do not adopt fp-ts v2 code in a v3 world.** fp-ts v3 changed `Either`/`Option` ergonomics and module paths. If you inherit an fp-ts codebase, check the version first — v2 tutorials (including most blog posts from 2021–2022) will not compile against v3.

**2. neverthrow does not compose across types.** `Result` and `ResultAsync` are separate types, and combining sync + async chains requires conversion (`asAsync`, `asResult`). If your pipeline mixes validation, IO, and retries, the conversions add noise — a sign you are outgrowing it.

**3. Effect's `yield*` requires `esModuleInterop` and a modern TS target.** The generator-based API needs TypeScript ≥5.0 and works best with `strict: true`. Effect also has an eslint plugin (`eslint-plugin-effect`) that catches common mistakes like unhandled effects.

**4. Error unions vs error classes.** With all three libraries, typed errors are unions of values — not classes with stack traces. When you hit the boundary (`runPromise`), wrap the failure in an `Error` with context for logging, or you lose stack information in production logs.

**5. Bundle size discipline.** neverthrow adds ~2 kB gzipped; fp-ts ~5–10 kB depending on imports; Effect can reach 30–60 kB even with tree-shaking. For a frontend bundle, measure before you commit. Effect shines server-side; neverthrow is the frontend-friendly option.

**6. Don't wrap everything.** If a function's error is truly unrecoverable (programming errors, invariant violations), letting it throw is fine. The libraries buy you the most at *boundaries*: parsing input, calling external services, reading config. Wrap those; leave inner assertions alone.

**7. Migrating neverthrow → Effect is mechanical at the boundaries.** `ok(x)` becomes `Effect.succeed(x)`, `err(e)` becomes `Effect.fail(e)`, `.andThen(f)` becomes `Effect.flatMap(f)` (or `yield*` in a generator), and `.match` becomes `Effect.match`. You can keep inner layers on neverthrow while outer layers adopt Effect, migrating function by function.

## FAQ

**What is the difference between Effect and fp-ts?**
fp-ts is a toolbox of algebraic types (`Option`, `Either`, `TaskEither`) composed with `pipe`. Effect is a complete runtime built on similar ideas: it adds typed failures integrated into a single `Effect<A, E, R>` type, structured concurrency, dependency injection via `Layer`, retry schedules, and observability. fp-ts gives you vocabulary; Effect gives you a platform.

**Is neverthrow worth it for a small project?**
Yes — it is the lowest-cost FP adoption available in TypeScript. One type (`Result`), no runtime, no pipe, and it works incrementally in existing codebases. If you only need to eliminate thrown errors, neverthrow is the right size.

**Which library has the most stars in 2026?**
Effect leads with 15,344 stars and is the most actively maintained (commits as of this week), followed by fp-ts at 11,538 and neverthrow at 7,675. Effect's star growth has been accelerating since its v3 release.

**Does Effect replace zod?**
Partially. Effect's `Schema` module provides runtime validation with `decodeUnknown`, but many teams still pair Effect with zod for its wider ecosystem. For a fresh Effect codebase, `Schema` avoids the extra dependency; see our [TypeScript schema validation comparison](../2026-08-12-zod-vs-valibot-vs-yup-typescript-schema-validation-comparison/) for the broader picture.

**Can I use these libraries with React or Express?**
Yes. neverthrow and fp-ts are framework-agnostic. Effect integrates with React via `@effect/react` and works inside Express/Fastify handlers by calling `Effect.runPromise` at the route boundary. State management interop is covered in our [JavaScript state management guide](../2026-07-05-javascript-state-management-redux-zustand-jotai-mobx-pinia/).

**What is the learning curve really like?**
neverthrow: hours. fp-ts: weeks to write idiomatic code, longer to read it fluently. Effect: expect 1–2 months before the type signatures feel natural — but the payoff is a coherent model for error handling, concurrency, and DI in one place.

**Is fp-ts dead?**
No — it is still maintained and widely used. But its ecosystem momentum has shifted to Effect: several prominent fp-ts ecosystem libraries were rewritten or abandoned after the v3 breaking change, while Effect's ecosystem (Effect, Schema, Stream, Cli, SQL) is the fastest-growing functional TypeScript stack in 2026.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "TypeScript Functional Programming in 2026: Effect vs fp-ts vs neverthrow — Which One Should You Actually Use?",
  "description": "Comparison of Effect, fp-ts, and neverthrow for functional programming in TypeScript: Result types, typed errors, structured concurrency, learning curves, bundle sizes, and migration paths.",
  "datePublished": "2026-08-19",
  "dateModified": "2026-08-19",
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
