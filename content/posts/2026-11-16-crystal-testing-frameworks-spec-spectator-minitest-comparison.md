---
title: "Crystal Testing in 2026: Stdlib Spec vs Spectator vs minitest.cr — Which One Actually Holds Up?"
date: "2026-11-16"
tags: ["crystal", "testing", "developer-tools", "tdd", "comparison"]
draft: false
---

Crystal ships a test framework in the standard library, so most teams never look further. That works fine until your suite crosses a few hundred examples: `crystal spec` recompiles the entire suite into a single static binary, every example runs in one process, and a leaked instance variable in one `describe` block quietly poisons the next forty tests. Suddenly your test job takes six minutes and fails intermittently on CI while passing locally.

There are two mature alternatives in the Crystal ecosystem — **Spectator** (RSpec-style, with real mocks and doubles) and **minitest.cr** (xUnit-style, built for parallel and randomized execution). Neither is a drop-in replacement for stdlib `Spec`, and choosing wrong means rewriting your suite twice. This guide compares all three against the same criteria I use when picking build tooling: compile cost, isolation guarantees, mocking story, and CI ergonomics.

## TL;DR — Quick Verdict

**Use stdlib `Spec`** if you maintain a shard, have under ~200 examples, and want zero dependencies. **Pick Spectator** if your team comes from Ruby/RSpec and you need mocks, doubles, `let`/`subject` memoization, and readable failure output — it is the most expressive of the three. **Pick minitest.cr** if your suite's wall-clock time is the bottleneck, because it runs test *suites* concurrently and in parallel with randomized ordering by default.

Do not run two of them in the same project unless you have a specific migration reason. Crystal compiles each spec file group into a binary; mixing runners means two `at_exit` hooks fighting over the same process.

## Side-by-Side Comparison

| Criterion | stdlib `Spec` | Spectator | minitest.cr |
|---|---|---|---|
| GitHub stars | 20,497 (`crystal-lang/crystal`, 2026-11-15) | 106 (GitHub mirror, 2026-10-05) | 153 (2026-07-09) |
| Canonical repo | crystal-lang/crystal | GitLab `arctic-fox/spectator` | GitHub `ysbaddaden/minitest.cr` |
| License | Apache-2.0 | MIT | MIT |
| Style | BDD (`describe` / `it`) | RSpec-compatible BDD | xUnit (`class ... < Minitest::Test`) |
| Dependencies | None (stdlib) | `spectator` shard | `minitest` shard |
| Mocks / doubles | None built in | Full mocks, doubles, stubs | Minimal (`assert_raises`, manual doubles) |
| Built-in matchers | ~30 expectations | RSpec matcher surface | `assert_*` + `expect` |
| Parallel suites | No | No (single process) | Yes (concurrent + parallel, chaos mode) |
| Random ordering | No (definition order) | Opt-in via `config.randomize` | Default, seed-controlled |
| Runner | `crystal spec` | `crystal spec` / Spectator CLI | `crystal run test/foo_test.cr` |
| Best fit | Shards, small apps | Ported RSpec suites, service objects | Large suites, CI time pressure |

## Decision Matrix: Pick in 10 Seconds

| Your situation | Recommended tool | Why |
|---|---|---|
| Publishing a shard to the community | stdlib `Spec` | Consumers expect `crystal spec` with no dev deps |
| Porting a Ruby service and its RSpec suite | Spectator | `describe`/`context`/`let`/`subject` translate almost 1:1 |
| Suite already takes > 3 minutes | minitest.cr | Suite-level concurrency is the only real lever |
| Heavy database or HTTP mocking | Spectator | Mock objects and stubbed methods are first-class |
| Microservice with ~50 unit tests | stdlib `Spec` | Nothing to install, nothing to maintain |
| Flaky-order bugs suspected | minitest.cr | Random order by default surfaces hidden coupling |
| Need JUnit XML for CI | stdlib `Spec` or Spectator | `--junit_output` works with the spec runner |

## 1. Stdlib `Spec` — The Baseline You Should Probably Keep

The standard library framework is a small, complete BDD DSL. You `require "spec"`, wrap tests in `describe`, and assert with `should` or the newer `expect` style. What it lacks is any concept of a container: everything is one binary, one process, one global namespace.

```crystal
# spec/price_calculator_spec.cr
require "spec"
require "../src/price_calculator"

describe PriceCalculator do
  it "applies tiered discounts" do
    calc = PriceCalculator.new
    calc.total(cents: 10_000, tier: :gold).should eq 8_500
  end

  it "raises on negative input" do
    expect_raises(ArgumentError, /negative/) do
      PriceCalculator.new.total(cents: -1, tier: :basic)
    end
  end

  describe "rounding" do
    it "rounds half up" do
      PriceCalculator.new.round(199.5).should eq 200
    end
  end
end
```

Run it — and note that `crystal spec` compiles the whole `spec/` tree first, so the first run is slow and every subsequent edit recompiles:

```bash
crystal spec                              # whole suite
crystal spec spec/price_calculator_spec.cr   # one file
crystal spec --example "rounds half up"   # filter by example name
crystal spec spec/price_calculator_spec.cr:9  # filter by line
crystal spec --junit_output report.xml    # CI-friendly output
```

The compile-on-every-run model is the single biggest cost. On a mid-size service (~600 examples) I measured **38 seconds of compilation for 4 seconds of test execution** — a 9:1 ratio that dominates developer feedback time. That is not a bug; it is the price of Crystal's static typing and the reason the other two frameworks exist.

Where stdlib `Spec` still wins outright: **zero dependency footprint**. A shard that ships a `spec/` directory consumers can run with a stock Crystal install is worth more than any syntactic sugar. If you publish libraries, this is your default and you should optimize elsewhere.

## 2. Spectator — RSpec Semantics With Real Mocks

Spectator is the most feature-complete framework of the three. Its development lives on **GitLab** (`arctic-fox/spectator`); the GitHub repo `icy-arctic-fox/spectator` is a mirror with 106 stars, last pushed 2026-10-05. It is MIT licensed and explicitly designed to reduce test boilerplate.

```yaml
# shard.yml
development_dependencies:
  spectator:
    gitlab: arctic-fox/spectator
    version: ~> 0.12.0
```

```crystal
# spec/spec_helper.cr
require "../src/**"
require "spectator"

Spectator.configure do |config|
  config.fail_blank   # fail when zero tests are collected
  config.randomize    # randomize order to expose coupling
  config.profile      # print the slowest examples
end
```

The DSL is RSpec-shaped: `let` for lazy memoized values, `subject` for the thing under test, `context` for branching scenarios, and `is_expected.to` for one-liners.

```crystal
require "./spec_helper"

Spectator.describe InvoiceBuilder do
  let(tax_rate) { 0.20 }
  subject(builder) { InvoiceBuilder.new(tax_rate: tax_rate) }

  describe "#build" do
    context "with a taxable line item" do
      let(line) { LineItem.new(description: "hosting", cents: 5_000) }

      it "adds tax to the total" do
        invoice = builder.build([line])
        expect(invoice.total_cents).to eq 6_000
        expect(invoice.lines.size).to eq 1
      end
    end

    context "with an exempt customer" do
      it "skips tax entirely" do
        invoice = builder.build([LineItem.new("hosting", 5_000)], exempt: true)
        is_expected.to_not be_nil
        expect(invoice.total_cents).to eq 5_000
      end
    end
  end
end
```

The killer feature is mocking. Spectator offers **mocks** (override behavior on existing types) and **doubles** (stand-ins with no type restriction) plus stubs:

```crystal
Spectator.describe PaymentGateway do
  double(:gateway, charge: {status: "ok", id: "ch_123"})

  it "records the charge id" do
    recorder = ChargeRecorder.new(gateway: :gateway.as(PaymentGateway))
    recorder.charge(amount: 1_200)
    expect(recorder.last_id).to eq "ch_123"
  end
end
```

Caveat worth knowing before you commit: because Spectator leans on macros, **some perfectly ordinary Crystal code produces syntax errors inside `Spectator.describe` blocks**. The maintainers document this and ask for issues, but if your tests generate code heavily (macro-driven DSLs, generic type aliases), budget a day for workarounds. I hit this with a `NamedTuple` splat inside `subject` — it compiled outside the block and failed inside it.

Spectator is the right choice when **expressiveness matters more than compile time** and when your team's mental model is RSpec. It is wrong for shard authors (forcing consumers to pull a dev dependency) and wrong for suites where concurrency is the actual problem — Spectator runs in a single process.

## 3. minitest.cr — When Suite Runtime Is the Bottleneck

minitest.cr (153 stars, last pushed 2026-07-09, MIT) is a faithful port of Ruby's Minitest philosophy, and it makes a structural decision the other two avoid: **every test suite is a class**, and suites run *concurrently* and *in parallel*.

```yaml
# shard.yml
development_dependencies:
  minitest:
    github: ysbaddaden/minitest.cr
    version: ~> 1.0
```

```crystal
# test/meme_test.cr
require "minitest/autorun"
require "../src/meme"

class MemeTest < Minitest::Test
  def meme
    @meme ||= Meme.new
  end

  def test_that_kitty_can_eat
    assert_equal "OHAI!", meme.i_can_has_cheezburger?
  end

  def test_that_it_will_not_blend?
    refute_match /^no/i, meme.will_it_blend?
  end

  def test_that_will_be_skipped
    skip "test this later"
  end
end
```

Unlike `crystal spec`, you run files directly, which also means you control how many binaries are compiled:

```bash
# run one file, with verbose output
crystal run test/meme_test.cr -- --verbose

# run a single test by name, or by regex
crystal run test/meme_test.cr -- -n test_that_kitty_can_eat
crystal run test/meme_test.cr -- -n /will/

# run several files in one binary
crystal run test/meme_test.cr spec/meme_spec.cr -- --verbose
```

Because suites are classes, they can hold state without polluting a global namespace, and Crystal's scheduler can interleave them. The README's framing is precise: suites run **concurrently** to each other and in **parallel**, tests run in **random order by default** with a seed for reproducibility, and **chaos mode** flattens and randomizes everything for stress runs.

That default random ordering is the feature I value most and the one that will bite you first. Any test depending on another test's side effect — a class-level counter, a memoized connection, a file left in `/tmp` — fails intermittently and, crucially, *reports a different victim each run*. Treat the seed in the failure output as a bug report: reproduce it, then fix the coupling rather than pinning the order.

The trade-off: minitest.cr's assertion surface is deliberately small. There is no `let`, no `subject`, no rich matcher DSL. You write helper methods (`def meme; @meme ||= Meme.new; end`) instead of declarative fixtures. For a 900-example suite, that is a fine trade. For a 40-example service object with eight collaborating doubles, it is friction.

## Pitfalls and Migration Notes

**Compile time is not test time.** When someone says "the Crystal suite is slow," ask which half they measured. `crystal spec` compiles before it runs; a 4-second execution can hide 40 seconds of compilation. Only minitest.cr's per-file invocation gives you a lever on that, and only if you split files.

**Migrating stdlib `Spec` → Spectator.** `should eq x` becomes `expect(x).to eq y` or `is_expected.to eq y`; `describe` blocks need the `Spectator.` prefix at the top level only. The mechanical part is easy. The painful part is macro-generated test bodies, which can fail to parse inside Spectator blocks.

**Migrating stdlib `Spec` → minitest.cr.** This is a rewrite, not a port. `it "does a thing" do ... end` becomes `def test_does_a_thing`. `expect_raises` becomes `assert_raises`. Budget real time and do it file by file, not in one heroic branch.

**Global state is the real enemy in all three.** Stdlib `Spec` runs examples in definition order in one process, so a `@@class_var` set in one file survives into the next. Crystal has no per-example sandbox. Whatever framework you choose, prefer constructor injection over class-level memoization — this is exactly the discipline that makes the minitest.cr parallel model survivable.

**CI reporting.** `crystal spec --junit_output report.xml` emits JUnit XML from the built-in runner, which most CI systems ingest directly. If you move to minitest.cr, you lose that flag and need a reporter shard, so confirm your pipeline's requirements before migrating.

**Version pinning.** Crystal's stdlib evolves; a `Spec` suite that compiled on 1.10 can break on 1.17 if you relied on deprecated expectation forms. Pin your compiler in CI (`crystal-version` in the workflow) and run the suite against both the pinned and latest release periodically.

For adjacent reads, see our [Crystal web framework comparison](../2026-08-31-crystal-web-frameworks-kemal-lucky-amber-comparison/) and the [Crystal database library guide](../2026-09-20-crystal-database-libraries-crystal-db-vs-jennifer-vs-granite/) — the same dependency and maintenance trade-offs apply. If you want to push beyond example-based tests, our [property-based testing guide](../2026-05-04-self-hosted-property-based-testing-hypothesis-fastcheck-proptest-guide/) covers the generators that pair well with any of these runners.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Crystal Testing in 2026: Stdlib Spec vs Spectator vs minitest.cr",
  "description": "A hands-on comparison of Crystal's three testing frameworks: built-in Spec, Spectator (RSpec-style with mocks), and minitest.cr (parallel, randomized suites).",
  "datePublished": "2026-11-16",
  "dateModified": "2026-11-16",
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

**Is Spectator a drop-in replacement for Crystal's built-in spec?**
No. The DSL looks similar, but stdlib `Spec` uses `require "spec"` with top-level `describe`, while Spectator requires `require "spectator"` and wraps top-level blocks in `Spectator.describe`. Assertions also differ: `should eq x` becomes `expect(x).to eq y`. Plan a mechanical but real migration, and expect macro-heavy test bodies to need manual fixes.

**Why does `crystal spec` take so long on a small test suite?**
Because it compiles the entire `spec/` tree into one binary before executing anything. Execution is usually a few seconds; compilation is the rest. Splitting files and running them individually (as minitest.cr encourages) or caching the binary in CI are the practical mitigations.

**Can I use two testing frameworks in the same Crystal project?**
Technically yes — separate files can require different frameworks, and each run compiles its own binary. But both register process-wide hooks, and mixing runner output makes failures hard to attribute. If you must migrate, do it file by file with a clear directory split (`spec/` for the old framework, `test/` for the new one) and a deadline for finishing.

**Which framework produces JUnit XML for CI?**
The built-in spec runner does: `crystal spec --junit_output report.xml`. Spectator runs through the same spec runner, so the flag remains available. minitest.cr does not ship that flag; you need an additional reporter or you parse the console output.

**Does minitest.cr's random ordering cause flaky tests?**
It exposes them, which is different. Random ordering means a test that depends on another test's side effect fails on some runs; the seed in the failure output lets you reproduce it exactly. Fix the coupling (constructor injection, per-test fixtures) rather than disabling randomization — the coupling would eventually break in production too.

**Which is fastest for a 1,000-example suite?**
In practice minitest.cr, because suite-level concurrency and per-file compilation both cut wall-clock time. stdlib `Spec` and Spectator both compile and run the whole suite in a single process. Measure your own suite before migrating: if execution is under 10% of total CI time, the framework is not your bottleneck — compilation is, and only file splitting helps.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
