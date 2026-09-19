---
title: "Haskell Effect Systems in 2026: effectful vs polysemy vs fused-effects vs mtl"
date: "2026-09-19"
tags: ["haskell", "functional-programming", "developer-tools", "effect-systems"]
draft: false
cover: "/img/screenshots/haskell-effect-systems-polysemy-logo.jpg"
description: "A hands-on comparison of Haskell's four main effect systems — effectful, polysemy, fused-effects and mtl — with real code, live GitHub activity data and a migration path off monad transformers."
---

Your `App` monad has grown to nine stacked transformers, the type signatures no longer fit on one line, and every new capability forces you to edit a `MonadFoo` instance chain that nobody on the team fully understands. That is the exact pain every Haskell team hits somewhere between 5k and 50k lines — and it is why effect systems exist.

But "use an effect system" is not advice, it is a fork in the road. Four libraries own this space in 2026, and they make genuinely different trade-offs around performance, ergonomics and how much the compiler can help you. This guide compares them with live repository data and real, runnable code pulled from each project's own documentation.

## TL;DR — Quick Verdict

**Pick `effectful` if you are building a new production service** — it is the fastest-maintained option (last commit September 2026), it integrates cleanly with `ReaderT IO`, and it has the least surprising performance profile. **Pick `mtl` if your team is already fluent in monad transformers** and your codebase is under ~10k lines; it is boring, ubiquitous and every tutorial assumes it. **Pick `fused-effects` if you care about interpreter fusion and want higher-order effects without a plugin.** **Pick `polysemy` only for existing projects or if you specifically need its first-class higher-order effects ergonomics** — it has been dormant since March 2025.

If you want one sentence: *effectful for greenfield, mtl for legacy, fused-effects for performance purists, polysemy for maintenance.*

## The Contenders at a Glance

All figures below were pulled from the GitHub API at publication time.

| Library | Stars | Last commit | Higher-order effects | Perf strategy | Compiler plugin |
|---|---|---|---|---|---|
| **[effectful](https://github.com/haskell-effectful/effectful)** | 485 | 2026-09-16 | Yes | `ReaderT IO` + `MonadUnliftIO`-friendly | No |
| **[polysemy](https://github.com/polysemy-research/polysemy)** | 1,074 | 2025-03-15 | Yes, first-class | `polysemy-plugin` for inference | Optional |
| **[fused-effects](https://github.com/fused-effects/fused-effects)** | 672 | 2026-05-06 | Yes | Carrier fusion | No |
| **[mtl](https://github.com/haskell/mtl)** | 402 | 2026-06-08 | Partially (`MonadReader`, `MonadState`) | Newtype-derived instances | No |

The star counts are misleading in one important way: `mtl` is the lowest-star entry here, but it ships with GHC's ecosystem and is a transitive dependency of an enormous share of Hackage. Popularity on GitHub and popularity in production are not the same metric.

## Scenario Decision Matrix

| Your situation | Recommended | Why |
|---|---|---|
| New service, team comfortable with `IO` | **effectful** | `Eff es` is a thin layer over `ReaderT IO`; no performance cliff, no plugin |
| Existing 50k-line `mtl` codebase | **mtl** | Migration cost outweighs the ergonomics win; stay put |
| Library author publishing to Hackage | **mtl** or **effectful** | `mtl` has zero ecosystem friction; `effectful` is the modern default |
| Benchmarking for max throughput | **fused-effects** | Carrier fusion removes intermediate `Bind` constructors |
| Need first-class `bracket`/`local` as effects | **effectful** or **polysemy** | Both expose higher-order effects without hand-written carriers |
| Maintaining an existing polysemy app | **polysemy** | Do not migrate a working system for star counts alone |

## effectful — The Modern Default

`effectful` takes the pragmatic route: instead of building a free-monad interpreter tower, it piggybacks on `ReaderT IO` for an effect *environment*, and uses the type-level list of effects to resolve which handler applies. The practical consequence is that your `Eff` computations are IO underneath, so performance is close to hand-written `ReaderT` code and you keep access to everything in the `IO` ecosystem.

```haskell
import Effectful
import Effectful.Reader.Static

program :: (Reader Int :> es, IOE :> es) => Eff es ()
program = do
  n <- ask
  liftIO (putStrLn ("count: " ++ show n))
```

What makes this usable day to day is that effect *dispatch* is resolved from the type-level list, so you never write `MonadFoo` instances by hand. Adding an effect means adding a constraint. Removing one means deleting a constraint and one handler from the runner stack.

The project is also the most actively maintained of the four — commits landed in September 2026 — which matters more than raw star count when you are betting your production codebase on an abstraction.

## polysemy — Higher-Order Effects, Elegant but Dormant

`polysemy` was the library that made higher-order effects approachable for people who did not want to write their own carriers. Its pitch is simple: effects are higher-order, so `bracket` and `local` are first-class rather than special-cased, and new effects take single-digit lines to define.

This is the real thing, straight from the project README. Define the effect with GADT constructors, run Template Haskell to generate smart constructors, then write interpreters as plain pattern matches:

```haskell
{-# LANGUAGE TemplateHaskell, LambdaCase, BlockArguments, GADTs
           , FlexibleContexts, TypeOperators, DataKinds, PolyKinds, ScopedTypeVariables #-}

import Polysemy
import Polysemy.Input
import Polysemy.Output

data Teletype m a where
  ReadTTY  :: Teletype m String
  WriteTTY :: String -> Teletype m ()

makeSem ''Teletype

teletypeToIO :: Member (Embed IO) r => Sem (Teletype ': r) a -> Sem r a
teletypeToIO = interpret \case
  ReadTTY      -> embed getLine
  WriteTTY msg -> embed $ putStrLn msg
```

Two things are worth noticing. First, the interpreter is just a function — no carrier type, no `Algebra` instance. Second, `interpret` versus `interpretH` is a real distinction: higher-order effects need the latter, and the library's error messages actually tell you so:

```txt
• 'Resource' is higher-order, but 'interpret' can help only
  with first-order effects.
  Fix:
    use 'interpretH' instead.
```

The catch is maintenance. `polysemy` last received a commit in March 2025. That does not make it broken — it is mature, widely used and the APIs are stable — but it does mean a new GHC release is a coordination risk you own. If you have a working `polysemy` service, keep it. If you are starting today, weigh that dormancy carefully.

`polysemy-plugin` exists to fix the type-inference friction that the free-monad encoding introduces. It genuinely works — it brings inference performance close to `mtl` — but adding it to `package.yaml` or your `.cabal` `ghc-options` section is one more moving part:

```haskell
{-# OPTIONS_GHC -fplugin=Polysemy.Plugin #-}
```

## fused-effects — Fusion, and the Cost of Higher-Order Effects

`fused-effects` is what you get when you take algebraic effects seriously and refuse to accept the interpreter overhead. Effect types are datatypes with one constructor per action, invoked via `send`. Carriers are monads with an `Algebra` instance describing how constructors are interpreted, and — this is the whole point — those carriers *fuse*, eliminating intermediate constructors that a naive free-monad encoding would allocate.

The README's own usage example shows the constraint style. Here is the `State` action, then a two-effect program combining `State` and `Reader`:

```haskell
action2 :: (Has (State String) sig m, Has (Reader Int) sig m) => m ()
action2 = do
  i <- ask
  put (replicate i '!')
```

Running effects means stacking handlers, each of which unpacks one carrier:

```haskell
example4 :: IO (Int, ())
example4 = runM . runReader "hello" . runState 0 $ do
  list <- ask
  liftIO (putStrLn list)
  put (length list)
```

The `Has` constraint is the interesting design decision. In `mtl`, `MonadState s m` is an instance-resolution problem and you are limited to a single state type per monad. With `Has`, the signature `sig` is explicitly named and multiple state types coexist, which is why the README has to tell you to annotate types (`list :: String`) to disambiguate. That flexibility costs annotation noise, and you feel it most in large functions with many effects.

`fused-effects` also documents the trade-off honestly: higher-order effects complicate fusion, and the project's comparison section against `polysemy`, `freer-simple` and `eff` is worth reading before you commit.

This is the real benchmark chart published in the `effectful` repository — it is exactly the kind of thing you should demand before trusting any performance claim about effect systems:

![Benchmark chart from the effectful repository comparing effect system overhead](/img/screenshots/haskell-effectful-benchmark.jpg "Effect system benchmark published in the effectful repository")

## mtl — Boring, Ubiquitous, Still Correct

`mtl` is not really a competitor to the other three; it is the baseline they are all defined against. `MonadState`, `MonadReader`, `MonadError` and friends are implemented via functional dependencies and newtype-derived instances, which is why `mtl` code can be extremely fast when the transformer stack is monomorphic — GHC's inliner does the work.

Where it hurts is scale. Each capability is a typeclass instance, the instance chain is hand-maintained, and capabilities that are higher-order in nature (`bracket`, scoped resource management) cannot be expressed as ordinary `MonadFoo` classes. That is the specific gap the other three fill. If you have never hit that wall, you do not have the problem these libraries solve — and `mtl` is the cheaper answer.

## Migration Notes and Pitfalls

**Do not migrate a working codebase to win an argument.** The most expensive outcome is a half-migrated stack where some modules use `Eff` and others use `AppM`, and every boundary needs a `runEff` or `runM` conversion. If you migrate, migrate leaf-first and keep the boundary at one module.

**Constraint creep is real.** In `fused-effects` and `polysemy`, every function that touches an effect grows its constraint list. In a well-factored codebase this is fine; in a module with twenty small helpers it becomes noise, and people start passing a monolithic constraint synonym that hides which effects are actually used — which defeats the purpose.

**The plugin is a dependency, not a detail.** `polysemy-plugin` changes type inference. That means error messages from a plugin-enabled build can differ from a build with the plugin off, and CI must use the same flags as production.

**Beware of "just use `ReaderT IO`" orthodoxy.** It is a legitimate answer for many applications, but it does not give you testable effect isolation — which is the thing effect systems actually buy you. If you are not writing interpreters for tests, you may not need an effect system at all.

**Check GHC support before adopting.** All four libraries track GHC releases on different schedules. Verify that your pinned GHC version is supported by the library you pick *before* you write 3,000 lines against it.

If you are building the surrounding application rather than the effect layer, our [Haskell web frameworks comparison](../2026-07-21-haskell-web-frameworks-yesod-scotty-servant/) covers how these constraints land in `servant` handlers, and the companion [Haskell testing frameworks guide](../2026-08-01-haskell-testing-frameworks-hspec-quickcheck-tasty-hunit/) shows how to structure tests against interpreted effects. When you are ready to pin the toolchain itself, the [Haskell build toolchain comparison](../2026-09-19-haskell-build-toolchain-cabal-stack-ghcup-hpack/) covers `cabal`, `stack`, `ghcup` and `hpack`.

## FAQ

**Which Haskell effect system should I use in 2026?**

`effectful` for new production code, `mtl` for existing transformer-based codebases, `fused-effects` when you need maximum throughput and are willing to write carriers, `polysemy` for existing projects or when you need its specific higher-order effect ergonomics. If you have no strong reason to pick otherwise, `effectful` is the safest default because it is the most actively maintained and has the least surprising runtime characteristics.

**Is polysemy abandoned?**

It is dormant rather than abandoned. The last commit to the repository was in March 2025 and the library has 1,074 stars with a stable API. Mature libraries with stable interfaces often stop receiving commits. Treat it as a maintenance liability only if you are tracking new GHC releases aggressively, and do not migrate a working `polysemy` service purely because of the quiet commit graph.

**Can I mix an effect system with plain IO code?**

Yes, and you probably should. `effectful` is explicitly designed around this: `Eff` is a thin layer over `ReaderT IO`, so `liftIO` drops you into ordinary IO whenever you need an existing library. `polysemy` and `fused-effects` both provide `Embed`/`Lift` effects for the same purpose. The practical pattern is to keep effects at your application boundary and pure IO at the edges.

**Are effect systems slower than hand-written monad transformers?**

Not necessarily, and the answer depends on the library. `fused-effects` was designed around carrier fusion specifically to remove the interpreter overhead that naive free-monad encodings pay. `effectful` sidesteps the question by being `ReaderT IO` underneath. `mtl` with a monomorphic stack is often the fastest of all because GHC inlines the entire transformer chain. Benchmark your actual workload rather than trusting a chart — including the official benchmark in the `effectful` repository.

**How hard is it to migrate from mtl to effectful?**

Mechanically it is a constraint rewrite: `MonadReader r m` becomes `Reader r :> es`, `MonadState s m` becomes `State s :> es`, and your `AppM` newtype disappears in favour of `Eff es`. The hard part is the boundary — every call into un-migrated code needs a run function. Budget for a leaf-first migration with a single conversion module rather than a big-bang rewrite.

**Do I need an effect system for a small application?**

Probably not. `ReaderT AppEnv IO` with a record of functions covers a large fraction of real applications, and it is trivially testable with a hand-written record of stubs. An effect system earns its complexity when you need multiple interpreters for the same capability — for example a real database interpreter and an in-memory interpreter used in tests — or when you need higher-order effects like scoped resource handling as first-class values.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Haskell Effect Systems in 2026: effectful vs polysemy vs fused-effects vs mtl",
  "description": "A hands-on comparison of Haskell's four main effect systems — effectful, polysemy, fused-effects and mtl — with real code, live GitHub data and migration guidance.",
  "datePublished": "2026-09-19",
  "dateModified": "2026-09-19",
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
