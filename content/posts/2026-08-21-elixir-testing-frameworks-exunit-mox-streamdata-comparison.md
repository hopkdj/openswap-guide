---
title: "Elixir Testing in 2026: ExUnit vs Mox vs StreamData — Which Stack Should You Use?"
date: "2026-08-21"
tags: ["elixir", "testing", "unit-testing", "developer-tools"]
cover: "/img/screenshots/elixir-cover.jpg"
draft: false
---

The BEAM is one of the few runtimes where the testing story ships with the language itself: every Elixir install bundles ExUnit, so a brand-new project already has a working test runner before you write a single line of application code. Yet the ecosystem around it is split into three distinct layers — ExUnit for structure, Mox for behaviour-driven mocks, StreamData for property-based generation — and picking the right combination is where most teams get stuck. In this guide we compare all three with real GitHub data and code straight from the official repositories, so you know exactly what each one is responsible for and when to reach for it.

**TL;DR:** ExUnit is the test framework — you will always use it, it needs zero setup, and it supports async test modules out of the box. Mox is the mock layer — use it the moment your code talks to external services or other modules, because it enforces explicit contracts and stays concurrency-safe. StreamData is the property-based testing layer — add it when you want to throw hundreds of randomized inputs at a function instead of hand-writing five examples. If you build Phoenix or Plug-based services, the trio works together: ExUnit runs the suite, Mox mocks the HTTP calls and mailers, StreamData fuzzes your parsers and validators. For a plain library with no external dependencies, ExUnit alone is genuinely enough.

## Quick Comparison: ExUnit vs Mox vs StreamData

| Dimension | ExUnit | Mox | StreamData |
|---|---|---|---|
| **Layer** | Test framework | Mocking library | Property-based testing + data generation |
| **Repository** | Ships inside `elixir-lang/elixir` | `dashbitco/mox` | `whatyouhide/stream_data` |
| **GitHub stars** | 26,603 (elixir repo) | 1,400 | 945 |
| **Last push** | 2026-08-21 | 2026-08-06 | 2026-07-14 |
| **License** | Apache-2.0 | Apache-2.0 | Apache-2.0 |
| **Dependencies** | None (stdlib of the language) | None at runtime | None at runtime |
| **Async-safe** | Yes (`async: true`) | Yes (same mock usable across async tests) | Yes |
| **Typical usage** | `test` blocks, `assert`, doctests | `Mox.defmock/2`, `expect/3` | `property` + `check all` |
| **Needs a behaviour?** | No | Yes (mocks only exist for behaviours) | No |

All three projects are healthy and actively maintained in 2026 — the oldest code in this comparison, Mox, still got a push within the last two weeks of this article's publication date.

## Use-Case Decision Matrix

| Use Case | Recommended Tool | Why |
|---|---|---|
| You want a test runner with zero config | **ExUnit** | Ships with Elixir; `mix test` just works |
| You're testing a module that calls an external API | **Mox** | Behaviour-based mocks with explicit contracts, no global state |
| You want your tests to run concurrently | **ExUnit + Mox** | `async: true` works with Mox mocks by design |
| You need to validate parsers, validators, or serializers | **StreamData** | Generates hundreds of edge-case inputs automatically |
| You're writing a pure library with no I/O | **ExUnit alone** | `assert` + doctests cover most pure functions |
| You're building a Phoenix application | **All three** | ExUnit for controllers, Mox for external services, StreamData for schemas |
| You need stateful model-based testing | **PropCheck/PropEr** (not StreamData) | StreamData explicitly does not support stateful testing yet |
| You want typespecs checked on every mock call | **Mox + Hammox** | Hammox verifies mock calls against behaviour typespecs |

## ExUnit — The Framework That Ships With Every Elixir Install

ExUnit is the unit testing framework bundled with Elixir itself, maintained in the same monorepo as the language (26,603 stars, last push the very day this article was written). Because it is part of the standard toolchain, there is no dependency to add, no version to pin, and no adapter to configure. The official module documentation shows the minimal setup:

```elixir
# File: assertion_test.exs

# 1) Start ExUnit.
ExUnit.start()

# 2) Create a new test module and use "ExUnit.Case".
defmodule AssertionTest do
  # 3) Note that we pass "async: true", this runs the tests in the
  #    test module concurrently with other test modules. The
  #    individual tests within each test module are still run serially.
  use ExUnit.Case, async: true

  # 4) Use the "test" macro instead of "def" for clarity.
  test "the truth" do
    assert true
  end
end
```

Under Mix, the runner looks for files matching `*_test.exs` under `test/` and loads `test/test_helper.exs` (which typically only calls `ExUnit.start()`) before executing anything. The features that keep ExUnit competitive five years after its nearest competitor went quiet: `setup`/`setup_all` callbacks, `@tag`-based filtering (including `@tag :skip` and `@tag :excluded`), `ExUnit.CaptureIO` for testing output, `ExUnit.CaptureLog` for log assertions, and `doctest Module` for running examples straight from your documentation.

The one gap: ExUnit deliberately has **no mocking story**. That is not an oversight — the maintainers' position, stated in the Mox design notes, is that ad-hoc mocks create more coupling than they remove. Mocks belong behind behaviours, and that is exactly what Mox provides.

## Mox — Mocks and Explicit Contracts, Without the Global State

Mox (1,400 stars, maintained by Dashbit, the company behind many core Elixir libraries, last push 2026-08-06) implements the philosophy from the famous *Mocks and explicit contracts* essay: **no ad-hoc mocks**, **no dynamic module generation during tests**, **concurrency support**. You can only mock a behaviour, which forces you to define the contract first. The official README walks through a complete flow — define a behaviour:

```elixir
# lib/weather_behaviour.ex
defmodule WeatherBehaviour do
  @callback get_weather(binary()) :: {:ok, map()} | {:error, binary()}
end
```

Implement it in production code, then create the mock in `test_helper.exs` and point your application at it:

```elixir
# In your test/test_helper.exs
Mox.defmock(WeatherBehaviourMock, for: WeatherBehaviour) # <- Add this
Application.put_env(:bound, :weather, WeatherBehaviourMock) # <- Add this

ExUnit.start()
```

Then in the test itself you use `expect` to assert on the arguments and control the return value, with `verify_on_exit!` guaranteeing every expectation was called:

```elixir
defmodule BoundTest do
  use ExUnit.Case

  import Mox

  setup :verify_on_exit!

  test "fetches weather based on a location" do
    expect(WeatherBehaviourMock, :get_weather, fn args ->
      assert args == "Chicago"
      {:ok, %{body: "Some html with weather data"}}
    end)

    assert {:ok, _} = Bound.get_weather("Chicago")
  end
end
```

Because the mock is defined once at compile time and expectations are set per-test, multiple test modules can use the *same* mock while running `async: true` — something most mocking libraries on other ecosystems still cannot guarantee. For teams that want typespecs enforced on every call, the README points to Hammox, an enhanced Mox that fails a test if a mock call doesn't match the behaviour's typespec. The cost of all this discipline: Mox is useless for mocking modules that do not declare a behaviour, and it cannot mock functions from modules you don't own (like `:httpc`). When you hit that wall, the idiomatic move is to wrap the external call in your own behaviour — which is usually the right design anyway.

## StreamData — Property-Based Testing and Data Generation for Elixir

StreamData (945 stars, written by Andrea Leopardi and José Valim, last push 2026-07-14) brings QuickCheck-style property testing to Elixir. Instead of writing a handful of hand-picked inputs, you declare a *property* that must hold for a whole class of inputs, and the library generates data to try to falsify it. The README's canonical example:

```elixir
use ExUnitProperties

property "bin1 <> bin2 always starts with bin1" do
  check all bin1 <- binary(),
            bin2 <- binary() do
    assert String.starts_with?(bin1 <> bin2, bin1)
  end
end
```

Generators are plain Elixir enumerables, which makes them usable outside property tests as ordinary infinite streams of data:

```elixir
StreamData.integer() |> Stream.map(&abs/1) |> Enum.take(3)
#=> [1, 0, 2]
```

and composable into arbitrarily complex custom generators:

```elixir
domains = ["gmail.com", "hotmail.com", "yahoo.com"]

email_generator =
  ExUnitProperties.gen all name <- StreamData.string(:alphanumeric),
                           name != "",
                           domain <- StreamData.member_of(domains) do
    name <> "@" <> domain
  end
```

The honest limitations, straight from the README's comparison section: StreamData does **not** support stateful property-based testing (model-based tests need PropCheck, a wrapper around Erlang's PropEr), and it does not store counter-examples in a file — you reproduce a failure by reusing the seed that caused it. For the majority of Elixir projects — parsers, validators, serializers, query builders — StreamData catches the edge cases (empty strings, unicode, huge integers) that nobody writes by hand, and it plugs into ExUnit through `ExUnitProperties` with zero infrastructure.

## Common Pitfalls and Migration Gotchas

1. **Mocking without a behaviour is the #1 mistake.** Newcomers try to mock modules like `HTTPoison` or `Jason` directly. Mox will not let you — and that is the point. Wrap the external client in your own module that declares a behaviour, then mock that. The extra module is the seam you will thank yourself for later.
2. **`async: true` breaks with global state.** The classic failure: a test writes to an ETS table, an Agent, or `Application.put_env/3` without `async: false`. ExUnit runs test *modules* concurrently, not just tests, so shared mutable state leaks across modules. Mox solves the mock half; the other half is discipline with processes and env.
3. **Doctest drift.** `doctest Module` is free documentation-as-tests, but stale doctests fail the build. Run `mix test` with doctests in CI and keep examples truthful — they are rendered into hexdocs for thousands of users.
4. **StreamData shrinking confusion.** When a property fails, StreamData reports the *smallest* failing input it found during shrinking. Developers sometimes assume the reported value is the original generated value and waste time chasing a "random" failure. The shrunk value is the bug, use it.
5. **Mox + `setup_all` expectations.** Expectations set in `setup_all` run once for the whole module; if an async sibling module calls the same mock, the expectation count races. Set expectations per-test (or per-`describe`) and use `setup :verify_on_exit!` so every test verifies its own contract.
6. **Forgetting `Application.put_env` for the mock switch.** A Mox mock that is never wired into the application config means your production module still calls the real implementation. The `test_helper.exs` pair — `Mox.defmock` *and* `Application.put_env` — must stay together.
7. **Property tests slow suites.** Generators default to generous iteration counts; if a property test takes seconds, tune the count (`check all ..., max_runs: 50`) rather than disabling it. A slow property test still beats a missing one.

For teams coming from RSpec or Jest, the mental model is familiar but the seams are stricter: RSpec-style loose mocks do not exist, and that strictness is precisely what keeps BEAM test suites fast and concurrent. Our [Ruby testing frameworks comparison](../2026-07-06-ruby-testing-frameworks-rspec-minitest-capybara/) and [JavaScript testing frameworks guide](../2026-07-21-javascript-testing-frameworks-vitest-jest-playwright/) cover how those ecosystems solve the same problems differently. If you are evaluating the whole Elixir stack, the [Phoenix vs Plug vs Ash web framework comparison](../2026-08-12-elixir-web-frameworks-phoenix-plug-ash-comparison/) shows where these testing tools plug into a real application, and the [property-based testing guide](../2026-05-04-self-hosted-property-based-testing-hypothesis-fastcheck-proptest-guide/) compares StreamData's approach with Hypothesis and fast-check.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Elixir Testing in 2026: ExUnit vs Mox vs StreamData — Which Stack Should You Use?",
  "description": "Compare ExUnit, Mox, and StreamData with live GitHub stats and official code examples. Learn which Elixir testing stack fits your project: unit tests, behaviour mocks, or property-based testing.",
  "datePublished": "2026-08-21",
  "dateModified": "2026-08-21",
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

### Does ExUnit include mocking support?

No. ExUnit deliberately has no mocking API. The Elixir ecosystem's answer is Mox, which only creates mocks for declared behaviours. If you need to fake a module without a behaviour, you wrap it behind your own behaviour first.

### Can I use Mox with `async: true` tests?

Yes. Mocks are defined once at compile time and expectations are set per-test, so multiple test modules can share the same mock while running concurrently. This is one of Mox's core design goals and a major reason teams pick it over dynamic-generation mocks.

### Is StreamData the same as property-based testing?

StreamData is the data-generation engine plus the `ExUnitProperties` integration; property-based testing is the technique of declaring properties and falsifying them with generated data. The library implements the technique for Elixir, modeled on the original QuickCheck paper and Clojure's test.check.

### What is the difference between Mox and Hammox?

Hammox is an enhanced version of Mox that also verifies every mock call against the behaviour's typespecs, catching mismatched argument and return types that plain Mox would miss. You can adopt it as a drop-in when you want the extra safety.

### When should I add StreamData to a project?

When your code takes unstructured input — parsers, validators, decoders, query builders — or when hand-written example lists keep missing edge cases. It integrates with ExUnit through `use ExUnitProperties` and costs nothing at runtime since it's a test-only dependency.

### Does ExUnit support test tags and filtering?

Yes. `@tag :skip`, `@tag :excluded`, and custom tags combine with `ExUnit.configure(exclude: ...)` and `mix test --only`/`--exclude` filters, letting you split smoke tests from full suites.

### Which testing stack should a new Elixir library use?

Start with ExUnit alone — it covers pure functions, doctests, and callbacks. Add Mox only when the library talks to external services or needs to swap implementations behind behaviours, and add StreamData when input parsing becomes part of the surface area.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
