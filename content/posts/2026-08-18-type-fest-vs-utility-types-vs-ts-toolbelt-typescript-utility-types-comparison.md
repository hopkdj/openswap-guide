---
title: "type-fest vs utility-types vs ts-toolbelt in 2026: Which TypeScript Utility Library Should You Use?"
date: "2026-08-18"
tags: ["typescript", "developer-tools", "frontend", "javascript"]
draft: false
cover: "/img/screenshots/typefest-cover.jpg"
---

TypeScript's built-in `Pick`, `Omit`, `Partial`, and `Record` cover maybe 20% of what your codebase actually needs. The other 80% — deeply optional config objects, camelCase conversions of API responses, "exactly one of these two fields" constraints — is why utility type libraries exist. They are the type-system equivalent of lodash: small, boring, and absurdly high-leverage. The problem is picking one, because the three serious candidates take three completely different philosophies.

**type-fest (17,362 stars)** is the curated essential kit with the best ergonomics. **utility-types (5,763 stars)** is a Flow-style API port with runtime type guards. **ts-toolbelt (7,151 stars)** is the lodash of types — the deepest, most advanced type-computation library on npm. All three are MIT-licensed and type-only (they add zero runtime bytes if you import correctly). They are not competitors in the way you'd expect: for most projects the real question is "type-fest, or type-fest plus one of the others."

## TL;DR / Quick Verdict

**Default to type-fest.** It's the only one of the three with a strong opinion about what *should* exist (no kitchen sink), requires TypeScript ≥ 5.9 with `strict` mode, and gives you the daily-driver types — `Except`, `PartialDeep`, `RequireAtLeastOne`, `CamelCase`, `PackageJson` — with the cleanest documentation in the ecosystem. **Add ts-toolbelt only when you hit type-level computation type-fest can't express** (advanced recursive/union manipulation) — its 200+ utilities come with a steeper learning curve and heavier language-server load. **Use utility-types when migrating from Flow** — its `$Keys`, `$Values`, `$ElementType`, `$Shape` API is the direct port, and its runtime type guards (`isPrimitive`, `isFalsy`, `isNullish`) are genuinely useful regardless.

## Quick Comparison Table

| Feature | type-fest | utility-types | ts-toolbelt |
|---|---|---|---|
| **GitHub stars** | 17,362 | 5,763 | 7,151 |
| **Last push** | 2026-08-15 | 2026-05-09 | 2025-06-02 |
| **Philosophy** | Curated essentials | Flow API port + guards | "Lodash of types" — largest set |
| **Type count** | ~400 (curated) | ~50 | 200+ (namespace-organized) |
| **TypeScript requirement** | ≥ 5.9, ESM, `strict: true` | Broad compatibility | ≥ 4.1, `strictNullChecks` advised |
| **Runtime helpers** | ❌ (types only) | ✅ Type guards + functions | ❌ (types only) |
| **Namespace modules** | ❌ Flat exports | ❌ Flat exports | ✅ `Object`, `Union`, `List`, `String`… |
| **IDE/language-server load** | Light | Light | Heavy on complex types |
| **Typical use** | Everyday API modeling | Flow migration, runtime checks | Advanced type-level programming |
| **Maintenance** | Very active | Active (slower) | Maintenance-mode cadence |
| **License** | MIT | MIT | MIT |

## Use-Case Decision Matrix

| Use Case | Recommendation | Why |
|---|---|---|
| Everyday API/config modeling | **type-fest** | `Except`, `Merge`, `PartialDeep`, `RequireAtLeastOne` map directly to real modeling pain |
| Migrating a codebase from Flow | **utility-types** | `$Keys`/`$Values`/`$ElementType`/`$Shape` are the exact Flow constructs, ported 1:1 |
| Runtime validation of primitives | **utility-types** | `isPrimitive`, `isFalsy`, `isNullish` are real type guards with type-level payoff |
| Deep type surgery on unions/lists | **ts-toolbelt** | Namespaced `Union.*`, `List.*`, `String.*` utilities for type-level computation |
| You need minimal IDE overhead | **type-fest** | Flat, shallow types keep the language server fast on large projects |
| Your tsconfig can't meet modern requirements | **utility-types** | Best compatibility with older TypeScript versions and non-ESM setups |

## type-fest — The Curated Essential Kit

type-fest is "a collection of essential TypeScript types" maintained by Sindresorhus, one of the most prolific open-source maintainers in the JavaScript ecosystem. Its defining trait is curation: instead of exposing 200 overlapping utilities, it ships the types that solve real, recurring problems, with docs that include playground links and examples for every entry.

```ts
import type {Except} from 'type-fest';

type Foo = {
	unicorn: string;
	rainbow: boolean;
};

type FooWithoutRainbow = Except<Foo, 'rainbow'>;
//=> {unicorn: string}
```

The catalog reads like a list of API-modeling pain points: `Merge` and `MergeDeep` for config inheritance, `RequireAtLeastOne` / `RequireExactlyOne` / `RequireAllOrNone` for mutually-exclusive fields, `PartialDeep` and `RequiredDeep` for nested option objects, `PickDeep` / `OmitDeep` for nested selection, `CamelCase` / `KebabCase` / `SnakeCase` for API key conversion, `Writable` and `WritableDeep` for immutable-to-mutable conversions, and `PackageJson` — an exhaustive typed model of `package.json` designed to be extended for tools that stash extra config in it:

```ts
import type {PackageJson as BasePackageJson} from 'type-fest';
import type {Linter} from 'eslint';

type PackageJson = BasePackageJson & {eslintConfig?: Linter.Config};
```

The trade-off is strict requirements: type-fest demands **TypeScript ≥ 5.9, ESM, and `strict: true`** in your tsconfig. That's a feature, not a bug — it refuses to support the legacy configs that make type gymnastics worse — but it means type-fest is not an option for legacy codebases pinned to older compiler versions. Its companion package `ts-extras` provides runtime functions for some of the types (like `String.camelCase`), and its exports are flat and shallow, keeping language-server load minimal even in huge projects. If you adopt exactly one library from this article, this is it.

## utility-types — Flow's API, Brought Home

utility-types positions itself as "a collection of utility types, complementing TypeScript built-in mapped types and aliases" — think lodash for static types. Its superpower is provenance: it ports the type operators that Flow developers know and love, which makes it the painless path for teams migrating away from Flow (a scenario that's still common in 2026 for React codebases that started in the 2010s).

```ts
$ElementType<T, K>   // the type of element at key K
$Values<T>           // union of all property value types
$Keys<T>             // union of all property keys
$Shape<T>            // every property of T becomes optional (Flow's Object.freeze helper)
$NonMaybeType<T>     // T without null | undefined
```

Where utility-types genuinely differentiates itself from the other two is **runtime code**: it ships actual TypeScript type guards. These are value-level functions whose return type narrows the parameter at compile time:

```ts
const consumer = (param: Primitive[] | Primitive): string => {
    if (isPrimitive(param)) {
        // typeof param === Primitive (narrowed!)
        return String(param) + ' was Primitive';
    }
    // typeof param === Primitive[]
    ...
};
```

`isPrimitive`, `isFalsy`, `isNullish` cover the most common runtime checks with correct narrowing — something neither type-fest nor ts-toolbelt offers, because they are strictly type-level. utility-types also includes a small functional API (mapped-type helpers applied to values) and marks a few legacy helpers deprecated (`getReturnOfExpression` — superseded by built-in `ReturnType` since TS 2.0). Its last push was May 2026 and its cadence is slower than type-fest's, but it's stable, complete software. Choose it for Flow migration and for the type guards; don't choose it for everyday type modeling when type-fest is available.

## ts-toolbelt — Type-Level Computation, Full Stop

ts-toolbelt is "TypeScript's largest type utility library" — 200+ utilities organized into namespaces that mirror the type system itself: `Any`, `Boolean`, `Class`, `Function`, `Iteration`, `List`, `Number`, `Object`, `String`, `Union`. It works "just like lodash, or ramda, but applied to the type system" — if you can compute it at runtime, someone has expressed it as a type here.

```ts
import {Object} from "ts-toolbelt"

// Merge two objects together
type merge = Object.Merge<{name: string}, {age?: number}>
// {name: string, age?: number}

// Make a field of an object optional
type optional = Object.Optional<{id: number, name: string}, "name">
// {id: number, name?: string}
```

Imports are namespaced — explicit (`import {Object, Union} from "ts-toolbelt"`), compact (`import {O, U}`), or portable (`import tb from "ts-toolbelt"`) — which keeps tree-shaking and readability sane despite the library's size. The depth here is real: `Union.Exclude`, `Union.Intersect`, `Union.Merge`, recursive list manipulation, string literal computation (`String.Replace`, `String.Split`), and advanced iteration types that let you write genuinely Turing-complete type programs.

The cost is paid in three places. First, **learning curve**: the API surface is enormous and the docs, while good, assume you know what you're looking for. Second, **language-server load**: deeply recursive conditional types are expensive to instantiate, and over-using ts-toolbelt types in large codebases measurably slows `tsc` and editor autocomplete. Third, **maintenance cadence**: the last push was June 2025, so it's effectively in maintenance mode — complete, but not evolving. Use ts-toolbelt when you genuinely need type-level computation; resist the temptation to import it "just in case," because the type-instantiation budget in a real project is not free.

## Common Pitfalls and Gotchas

1. **Importing types as values.** `import {Except} from 'type-fest'` without `type` keyword works at runtime because the import is erased — but with `verbatimModuleSyntax` (increasingly the default), it errors. Use `import type` everywhere and never pay runtime bytes for type-only libraries.
2. **Adopting type-fest on an old tsconfig.** It requires TS ≥ 5.9, ESM, and `strict: true`. If your project can't meet those, it silently breaks — check your `tsconfig.json` first, and use utility-types if you're stuck on an older compiler.
3. **Using ts-toolbelt as a default import.** The "portable" `import tb from "ts-toolbelt"` form imports the whole namespace, which can confuse the language server's type instantiation budget. Prefer explicit namespace imports (`Object`, `Union`) that you actually use.
4. **Over-deep types in shared libraries.** A utility type with 5 levels of recursion is fine for you and brutal for every consumer of your published package. Type instantiation depth limits (`TS2589`) are real; keep public APIs shallow.
5. **Duplicate type systems in one codebase.** Mixing type-fest, ts-toolbelt, *and* utility-types in the same project creates overlapping `Merge`/`Optional`/`Partial` types with subtly different semantics. Pick one primary (type-fest) and add a second only for its unique features (guards from utility-types, computation from ts-toolbelt).
6. **Treating runtime guards as validation.** `isPrimitive` narrows types at compile time; it does not validate untrusted input at runtime. For API payload validation, reach for a schema library — see our [Zod vs Valibot vs Yup comparison](../2026-08-12-zod-vs-valibot-vs-yup-typescript-schema-validation-comparison/) and the [TypeBox vs ArkType vs Runtypes guide](../2026-07-24-typescript-schema-validation-typebox-arktype-runtypes/).
7. **Ignoring the built-ins.** Before adding any dependency, check whether a newer TypeScript built-in covers the case. `Awaited<T>`, `NoInfer<T>`, `satisfies`, and template literal types have absorbed several formerly-external utilities — a good reason to re-audit utility-type imports on every TypeScript major upgrade.

## Choosing the Right Tool for Type Modeling

Utility type libraries and schema validation libraries answer different questions, and teams frequently blur the line. Utility types shape *existing* values (make fields optional, rename keys, extract unions) at compile time only — they add no runtime safety. Schema libraries validate *untrusted* values (HTTP requests, file input, third-party payloads) at runtime and derive types from the schema. A production TypeScript stack usually needs both: type-fest (or ts-toolbelt) for modeling your domain types, and a schema library at the boundaries — the pattern covered in depth in our [TypeScript schema validation comparisons](../2026-08-12-zod-vs-valibot-vs-yup-typescript-schema-validation-comparison/). For the broader TypeScript ecosystem picture — routing, data fetching, and state — our [React Router vs TanStack Router vs Wouter comparison](../2026-08-13-react-router-vs-tanstack-router-vs-wouter-typescript-comparison/) is a good companion read.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "type-fest vs utility-types vs ts-toolbelt in 2026: Which TypeScript Utility Library Should You Use?",
  "description": "Compare type-fest, utility-types, and ts-toolbelt for TypeScript utility types in 2026: curated essentials vs Flow API port vs type-level computation, GitHub stats, and decision matrix.",
  "datePublished": "2026-08-18",
  "dateModified": "2026-08-18",
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

### Which TypeScript utility library should I use in 2026?

Default to type-fest — it has the best ergonomics, the most active maintenance (last push August 2026), and covers 90% of real modeling needs. Add ts-toolbelt for advanced type-level computation and utility-types for Flow migration or runtime type guards.

### What TypeScript version does type-fest require?

TypeScript ≥ 5.9 with ESM and `strict: true` in tsconfig. This is a deliberate minimum — the library refuses to support legacy configurations. If you're pinned to an older compiler, utility-types offers the broadest compatibility.

### Do these libraries add to my bundle size?

No — they are type-only. Using `import type` ensures zero runtime code. The one exception is utility-types, which also ships runtime type guards (`isPrimitive`, `isFalsy`, `isNullish`) that add bytes only if you actually import and use them.

### Is ts-toolbelt still maintained?

The last push was June 2025, placing it in maintenance mode — complete and stable, but not actively evolving. Its 200+ utilities remain fully usable, and the community remains active in discussions.

### Can I use these with React or Node projects?

Yes — they're compiler-level libraries and work anywhere TypeScript runs: React apps, Node backends, monorepos, and shared packages. They're particularly common in API client and SDK codebases where complex response shapes need modeling.

### How do utility types differ from schema validation libraries?

Utility types work at compile time on values you already have; schema libraries validate untrusted input at runtime. For API payloads you need the runtime layer — our [TypeBox vs ArkType vs Runtypes comparison](../2026-07-24-typescript-schema-validation-typebox-arktype-runtypes/) breaks down the options.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
