---
title: "Erlang Testing in 2026: EUnit vs Common Test vs PropEr — Which One Should You Actually Use?"
date: "2026-09-07"
tags: ["erlang", "testing", "unit-testing", "property-based-testing", "otp", "beam"]
draft: false
---

The BEAM is forgiving in production — a crashing process restarts, a supervisor retries, and the system keeps answering requests while your bug quietly resets state. That resilience is exactly why Erlang projects accumulate untested code: it feels like nothing ever breaks. Then you deploy the release that drops a message every 100,000th call under load, and no amount of `io:format` debugging finds it. **Erlang ships two full testing frameworks inside OTP — EUnit and Common Test — and the BEAM ecosystem adds a third, PropEr, that attacks the failure class the other two cannot see.** Most teams use one of them and miss what the other two do.

## TL;DR — Quick Verdict

**Unit-testing pure functions and modules? Use EUnit** — it is in OTP, needs zero configuration, and its auto-discovery of `*_test()` functions means tests live next to the code they verify. **Testing stateful services, protocols, and multi-node behavior? Use Common Test** — it is the harness OTP itself uses, with per-suite and per-testcase fixtures plus HTML reports your QA team can actually read. **Want to find the bugs you have not thought of? Add PropEr** — property-based tests generate thousands of inputs and check invariants instead of examples. The pragmatic 2026 stack is **EUnit for unit tests, Common Test for integration suites, and PropEr properties hosted inside EUnit** — all three coexist in one project, and the first two cost you nothing extra.

## Quick Comparison Table

| | EUnit | Common Test | PropEr |
|---|---|---|---|
| Primary role | Unit testing | Integration / system testing | Property-based testing |
| Ships with OTP | ✅ Yes | ✅ Yes | ❌ No (hex.pm / GitHub) |
| Test discovery | Auto-exported `*_test()` functions | Mandatory `all/0` callback | Explicit `proper:quickcheck/1` |
| Assertions | `?assert`, `?assertEqual`, pattern matching | `?assert` macros + return-value checks | Implication + `?FORALL` generators |
| Fixtures | `setup`/`cleanup` in module | `init_per_suite`/`end_per_suite` + per-testcase | `?LET` bindings, generator composition |
| Parallelism | `eunit:test({inparallel, M})` | Testcase groups, parallel group type | Properties run sequentially (fast anyway) |
| HTML reports | No | ✅ Yes — `ct_run` logs every step | No (text output, optionally to `user`) |
| License | Apache-2.0 (OTP) | Apache-2.0 (OTP) | GPL-3.0-or-later |
| Repo / stars | `erlang/otp` — 12,347⭐ | `erlang/otp` — 12,347⭐ | `proper-testing/proper` — 918⭐ |
| Latest activity | 2026-09-04 (OTP 29 line) | 2026-09-04 (common_test v1.31.1) | 2026-06-24 (v1.5.0, Erlang 21.3–29.0) |

## Decision Matrix — Which One for Your Use Case?

| Use case | Recommended tool | Why |
|---|---|---|
| Test a pure function (lists, maps, parsers) | EUnit | Zero setup, inline `_test()` functions, sub-second runs |
| Test a `gen_server` / `gen_statem` lifecycle | Common Test | `init_per_testcase` gives you a clean process tree per case |
| Verify a protocol against a real peer (or another node) | Common Test | Suite-level fixtures, timeouts, and HTML step logs |
| Prove an invariant holds for 10,000 random inputs | PropEr (hosted in EUnit) | Example-based tests cannot sample the input space |
| Regression suite for CI that must finish fast | EUnit | `{inparallel, M}` runs module tests across schedulers |
| Acceptance/system test with reports for managers | Common Test | `ct_run` output is the closest thing to a test report the BEAM has |

## EUnit — The Unit-Level Default That Ships With OTP

EUnit has been in OTP since R12, which means it is on every Erlang system you will ever touch — no dependency to vendor, no version to pin. Its model is deliberately small: write functions whose names end in `_test` (or `_test_` for generators) and EUnit finds, runs, and reports them automatically when you call `Module:test()` or `eunit:test(Module)`.

The canonical module under test plus test file lives in one source unit:

```erlang
-module(reverse).
-export([reverse/1]).

reverse([]) -> [];
reverse([H | T]) -> reverse(T) ++ [H].
```

```erlang
-module(reverse_tests).
-include_lib("eunit/include/eunit.hrl").

reverse_test() -> lists:reverse([1, 2, 3]).

reverse_nil_test() -> [] = lists:reverse([]).

length_test() -> ?assert(length([1, 2, 3]) =:= 3).

%% Generators — functions ending in _test_ return a list of tests
basic_test_() -> ?_assert(1 + 1 =:= 2).
```

Three idioms are worth internalizing. First, **a bare expression as a test body doubles as the assertion** — `reverse_nil_test() -> [] = lists:reverse([]).` fails with a badmatch and EUnit reports the mismatch. Second, **generators** (`_test_` suffix) let one function produce many assertions — combine with `?_assert`, `?_assertEqual`, and `?_assertMatch` for data-driven cases. Third, the convention of a **separate `m_tests` module** keeps test code out of production modules while still letting `eunit:test(m)` discover everything.

Run them from the Erlang shell:

```erlang
1> c(reverse_tests).
{ok, reverse_tests}
2> eunit:test(reverse_tests).
  All 4 tests passed.
ok
3> eunit:test({inparallel, reverse_tests}).   %% parallel across schedulers
```

Because EUnit is a library, not a harness, you can invoke it from `ct_run`, from a shell script in CI, or from `rebar3 eunit` — it composes with everything else on the BEAM. For our [Erlang JSON comparison](../2026-09-05-erlang-json-libraries-jiffy-jsx-jsone-comparison/) we noted how small the core libraries are; EUnit is the same philosophy applied to testing.

## Common Test — The Integration Harness OTP Itself Uses

Common Test (CT) is the framework the OTP team uses to test OTP. Where EUnit assumes a function, CT assumes a **testcase that returns a value**, a **suite module** that declares its cases, and **fixture callbacks** that set up and tear down state around them. Its reports — step-by-step HTML logs with timings and returned values — are why CT remains the default for protocol and system testing.

A minimal suite is almost embarrassingly short:

```erlang
-module(my1st_SUITE).
-compile(export_all).

all() -> [mod_exists].

mod_exists(_) ->
    {module, mymod} = code:load_file(mymod).
```

Run it with the `ct_run` executable or from the shell:

```bash
$ ct_run -dir .
$ ct_run -suite my1st_SUITE
```

```erlang
1> ct:run_test([{suite, "my1st_SUITE"}]).
```

The power shows up with fixtures. `init_per_suite/1` and `end_per_suite/1` bracket the whole suite; `init_per_testcase/2` and `end_per_testcase/2` bracket every case, and they pass a `Config` list of `{Key, Value}` tuples down the chain:

```erlang
-module(check_log_SUITE).
-export([all/0, init_per_suite/1, end_per_suite/1,
         init_per_testcase/2, end_per_testcase/2]).

all() -> [log_exists, log_rotates].

init_per_suite(Config) ->
    application:ensure_all_started(myapp),
    [{app_dir, "/tmp/myapp-log"} | Config].

init_per_testcase(_, Config) ->
    {ok, Pid} = myapp_log:start(proplists:get_value(app_dir, Config)),
    [{log_pid, Pid} | Config].

end_per_testcase(_, Config) ->
    myapp_log:stop(proplists:get_value(log_pid, Config)).

log_exists(Config) ->
    true = filelib:is_dir(proplists:get_value(app_dir, Config)).
```

Testcases can also return `{skip, Reason}` (mark a case skipped instead of failed), `{comment, Text}` (annotate the log), and `{save_config, Config}` (hand state to the next case). Suite groups — `{group, parallel_group}` with `parallel` as the group type — run cases concurrently when order does not matter.

CT is the right tool when your test needs **more than one process, real sockets, or a whole node**. It is the natural partner for the servers covered in our [Erlang HTTP server comparison](../2026-09-04-erlang-http-servers-cowboy-mochiweb-yaws-comparison/) — spin the server up in `init_per_suite`, hit it with real HTTP from testcases, and tear it down in `end_per_suite`.

## PropEr — Finding the Bugs You Did Not Think Of

Example-based tests encode what you already believe about the code. Property-based tests encode what must *always* be true — then a generator explores the input space for a counterexample. PropEr (from *PROPerty-based testing for ERlang*) is the mature BEAM implementation, and it is the Erlang sibling of the Hypothesis/QuickCheck family we covered in our [property-based testing guide](../2026-05-04-self-hosted-property-based-testing-hypothesis-fastcheck-proptest-guide/).

Get it on the path and include the header:

```bash
$ export ERL_LIBS=/full/path/to/proper
```

```erlang
-module(prop_reverse).
-include_lib("proper/include/proper.hrl").

prop_reverse_is_involution() ->
    ?FORALL(L, list(integer()),
            lists:reverse(lists:reverse(L)) =:= L).
```

Run it:

```erlang
1> proper:quickcheck(prop_reverse:prop_reverse_is_involution()).
..............................................................................
OK, passed 100 tests
true
```

When a property fails, PropEr prints the minimal counterexample — it shrinks the failing input automatically, which is where property testing earns its keep: the 47-element list that breaks your parser shrinks to `[0]`, and suddenly the bug is obvious. The library supports Erlang 21.3 through 29.0, publishes v1.5.0 to hex.pm, and stays active (last push June 2026).

**Licensing is the one real difference to plan for**: EUnit and Common Test are Apache-2.0 inside OTP, but PropEr is **GPL-3.0-or-later**. For internal test suites that never ship, that is a non-issue — the license does not infect your application code. If you distribute test tooling built on PropEr or embed it in a closed product, get advice first.

## The Testing Pyramid on the BEAM

A realistic 2026 Erlang project uses all three without ceremony:

1. **EUnit** for every module: pure functions get `m_tests` modules, run in CI with `rebar3 eunit` — seconds.
2. **Common Test** for every service boundary: `gen_server` start/stop cycles, database round-trips, and the HTTP endpoints of your [Cowboy or Mochiweb services](../2026-09-04-erlang-http-servers-cowboy-mochiweb-yaws-comparison/) — minutes, with HTML evidence.
3. **PropEr** for the invariants: parse/format round-trips, state-machine transitions, and anything where hand-written examples feel thin. Host the properties inside an EUnit `_test_` generator so one command runs everything.

The same layering exists across the BEAM family — Elixir teams mirror it with ExUnit, Mox, and StreamData, as our [Elixir testing comparison](../2026-08-21-elixir-testing-frameworks-exunit-mox-streamdata-comparison/) shows — so the pattern transfers if your codebase mixes languages.

## Pitfalls and Migration Notes (What Nobody Tells You)

- **EUnit swallows stdout, and PropEr output vanishes with it.** EUnit captures standard output during tests, so `proper:quickcheck/1` results printed to stdout never appear. Run properties with output redirected to the `user` process: `proper:quickcheck(Prop, [{to_file, user}])` — or use `io:format(user, ...)` in your own code.
- **`?LET` macro collision between PropEr and EUnit.** Both headers export a `?LET` macro, and include order decides which one wins — with confusing results. Include `proper.hrl` **before** `eunit.hrl` in any module that uses both, or wrap PropEr properties in a separate module that only includes `proper.hrl`.
- **Common Test requires `all/0` — always.** Forget it and the suite fails at load time with a `undef` error, not a friendly message. `-compile(export_all)` in examples hides this; be explicit in real suites.
- **EUnit badmatch tests fail with raw badmatch errors.** `[] = lists:reverse([])` is idiomatic but reports `badmatch` without context. For readable failures use `?assertEqual` or `?assertMatch` with a message argument.
- **CT HTML logs grow without bound on long suites.** Configure `{logdir, ...}` and clean old runs in CI — a week of nightly `ct_run` runs will happily produce gigabytes.
- **Generator tests are only as good as their generators.** `list(integer())` will not find the bug that needs non-empty, sorted, or Unicode lists. Build domain generators with `?LET` and `suchthat` filters — the extra 10 lines are where the value is.
- **GPL boundary:** if your company policy bans GPL even for test-only code, PropEr is the odd one out — check the license before standardizing the team template.

## FAQ

**Do I need to install anything for EUnit and Common Test?**
No — both ship inside OTP. `eunit` and `common_test` are standard applications in every Erlang/OTP release since forever; PropEr is the only one of the three you install yourself (hex.pm package `proper` or the GitHub repo).

**Can EUnit and Common Test run in the same project?**
Yes, and most serious projects use both. `rebar3` runs EUnit via `rebar3 eunit` and Common Test via `rebar3 ct`; a CI pipeline typically runs EUnit first (fast feedback) and CT second (integration coverage).

**Can I run PropEr properties from within EUnit or Common Test?**
Yes. EUnit generators (`_test_` functions) can call `proper:quickcheck/1` directly, and CT testcases can call it too. Remember the stdout capture pitfall — pass `[{to_file, user}]` or assert on the boolean result (`true = proper:quickcheck(...)`).

**Which framework does the OTP team itself use?**
Common Test. OTP's own test suites for `ssl`, `ssh`, `megaco` and the rest are CT suites, which is the strongest possible endorsement of the harness for protocol-level and system-level testing.

**Is Common Test only for black-box system testing?**
It is most famous for that, but CT testcases are plain Erlang functions with fixtures — teams use it for white-box unit-ish tests whenever they need `init_per_testcase` isolation or HTML reporting. The cost is more boilerplate than EUnit, so reserve it for where its fixtures pay off.

**What Erlang versions does PropEr support?**
v1.5.0 supports Erlang 21.3 through 29.0, covering every release most teams run in 2026.

**How do I parallelize my Erlang tests?**
EUnit: `eunit:test({inparallel, Module})` (or `{inparallel, [Modules]}`). Common Test: declare a group `{group, Name, [parallel], Cases}` in `all/0`. Be careful with shared state — parallel tests and `mnesia` or ETS tables need explicit coordination.

**Why does my test pass locally but fail in CI?**
The usual suspects: CT `Config` paths that assume a checkout directory, EUnit stdout capture hiding a `io:format` you were relying on for debugging, and property tests whose random seed differs per run — PropEr accepts a seed via `{seed, ...}` options if you need reproducible failures.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Erlang Testing in 2026: EUnit vs Common Test vs PropEr — Which One Should You Actually Use?",
  "description": "Hands-on comparison of the three Erlang testing tools: EUnit and Common Test (both built into OTP) and the PropEr property-based testing library. Covers fixtures, parallelism, HTML reports, licensing, and how to combine all three in one project.",
  "datePublished": "2026-09-07",
  "dateModified": "2026-09-07",
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
