---
title: "Perl Testing in 2026: Test2::V0 vs Test::More vs Test::Deep — Which Stack Should You Run?"
date: "2026-10-20"
tags: ["perl", "testing", "devops", "developer-tools"]
draft: false
description: "A practical 2026 comparison of Perl's testing stacks: Test2::V0, the classic Test::More and Test::Deep, with real synopsis code, TAP output, parallelism and migration pitfalls."
---

Perl has been shipping a test framework in core since 2001, which is both a gift and a trap. The gift is that `prove` and `Test::More` are there on every machine, with zero dependencies — you can test a script on a bare container image. The trap is that a decade of accumulated work sits behind a module most teams never migrate to: **Test2**, an event-based framework that fixes the architectural limits of the classic API, and which now powers CI suites that Test::More simply cannot express cleanly.

If your `t/` directory still starts with `use Test::More tests => 42;`, this is the comparison you need. Three stacks are in play, and they are not competitors so much as layers: **Test2::V0** is the modern bundle, **Test::More** is the compatibility layer you already have, and **Test::Deep** is the structural-comparison tool that neither replaces.

## TL;DR — the verdict

**New projects: use Test2::V0.** It gives you `ok`, `is`, `like`, `is_deeply`, `subtest`, `done_testing` and rich diagnostics in one import, on top of an event architecture that supports concurrency and tooling. **Legacy suites: stay on Test::More** until you have a reason to move — it is core, ubiquitous, and Test2::V0 is largely a superset, so migration is incremental rather than a rewrite. **Any suite that compares nested data structures: add Test::Deep** regardless of which of the other two you use. It is the one component with no real substitute in core, and its `cmp_deeply` with `bag`, `array_each`, `ignore` and `methods` handles the cases where `is_deeply` gives you an unreadable diff.

## Side-by-side comparison

| Dimension | Test2::V0 | Test::More | Test::Deep |
|---|---|---|---|
| Ships with Perl core | No (install `Test2::Suite`) | **Yes (since 5.8)** | No |
| Architecture | Event-based (`Test2::API` hub) | Assertion-based, TAP direct | Assertion helpers |
| GitHub repo | `Test-More/Test2-Suite` | Test-Simple dist (CPAN) | `rjbs/Test-Deep` |
| GitHub stars | 25 | n/a (core module) | 15 |
| Last commit / release | 2024-08-04 | actively released on CPAN | **2026-02-22** (6.78, 2025-04-01) |
| Diagnostics on failure | **Structured, coloured, context-rich** | Plain `#` comment lines | Detailed structure diff |
| Subtests | Yes (`subtest`) | Yes (`subtest`, since 1.3) | n/a |
| Concurrency / parallel-safe | **Yes — designed for it** | No (global state) | Inherits host framework |
| Custom tools / plugins | **Yes (`Test2::Tools::*`)** | Limited | No |
| Deep structure matching | Basic (`is_deeply`) | Basic (`is_deeply`) | **Advanced (`cmp_deeply`)** |
| Learning curve | Medium | **Lowest** | Low |
| Migration cost from Test::More | Low (superset) | — | Additive |

Star counts and last-push dates pulled from the public repositories on 2026-10-20. Test::Deep's CPAN release 6.78 is dated 2025-04-01.

## Decision matrix

| Your situation | Pick | Why |
|---|---|---|
| Brand-new Perl project, 2026 | **Test2::V0** | One import, modern diagnostics, parallel-safe |
| Existing 5,000-test legacy suite | **Test::More**, migrate file by file | Zero-risk, incremental, same assertions |
| Comparing nested hashes/objects | **Test::Deep** | `cmp_deeply` with flexible matchers |
| Tests must run under `prove -j8` | **Test2::V0** | Event hub isolates per-test state |
| CI needs machine-readable results | **Test2::V0 + TAP::Harness** | Structured events, plugin ecosystem |
| You cannot install CPAN modules | **Test::More** only | Core-only environments |

## Test2::V0 — the modern bundle

Test2's central idea is that a test run is a stream of *events*, not a sequence of print statements. Assertions, diagnostics, subtest boundaries and plan changes are all events posted to a hub, which formats them into TAP (or anything else) at the end. That indirection is why Test2 can support concurrency, custom formatting, and tools that introspect results, all of which are bolted onto Test::More at best.

The entry point is deliberately minimal:

```perl
use Test2::V0;

ok(1, "pass");

...

done_testing;
```

That import pulls in the whole default toolset — `ok`, `is`, `isnt`, `like`, `unlike`, `is_deeply`, `subtest`, `note`, `diag`, `done_testing` — so a file converted from Test::More usually compiles after changing one line. The failure output is where the difference is obvious: instead of `#          got: 'foo'` and `#     expected: 'bar'`, you get a structured comparison showing exactly which element diverged, with the surrounding structure rendered.

Subtests are first class:

```perl
use Test2::V0;

subtest 'cache eviction' => sub {
    my $cache = build_cache(ttl => 1);
    $cache->set(k => 'v');
    ok $cache->get('k'), 'value present';
    sleep 2;
    is $cache->get('k'), undef, 'value expired';
};

done_testing;
```

Two practical notes for 2026. First, Test2::V0 often collides with `Moose`, because both export `meta()`. The documented fix is to import with `'!meta'`, which skips the conflicting sub (a `meta_check()` alias is provided). Second, the bundle has import tags (`:DEFAULT`) and pragmas so you can opt into `strict`, `warnings` and `utf8` from the same line — a small thing that removes three lines from every test file.

The honest caveat: Test2::Suite is not in core, so using it means a CPAN dependency. That is trivial on any modern Perl, but it is a real constraint in air-gapped or minimal-container environments where only core modules exist.

## Test::More — the compatibility layer that refuses to die

Test::More's synopsis has barely changed in twenty years, and that is precisely its value:

```perl
use Test::More tests => 23;
# or
use Test::More skip_all => $reason;
# or
use Test::More;   # see done_testing()

require_ok( 'Some::Module' );

# Various ways to say "ok"
ok($got eq $expected, $test_name);

is  ($got, $expected, $test_name);
isnt($got, $expected, $test_name);

# Rather than print STDERR "# here's what went wrong\n"
diag("here's what went wrong");

like  ($got, qr/expected/, $test_name);
unlike($got, qr/not_expected/, $test_name);
```

Every Perl developer can read that file. Every tutorial, every legacy codebase, every Stack Overflow answer assumes it. When you hire someone to work on a 2014 Perl service, they will be productive in `Test::More` on day one and will need an afternoon to learn Test2's event model.

The architectural limits are equally well known. Global test state makes parallel execution inside a single process hazardous. Diagnostics are strings, so tooling has to parse them. There is no plugin layer to speak of. And the `tests => 23` plan means adding an assertion in the middle of a file requires updating a number at the top — the single most common cause of "planned 23 tests but ran 24" failures in Perl CI.

Use `done_testing()` instead of a fixed plan wherever you can. It costs nothing and removes that failure mode entirely, and it works in Test::More just as well as in Test2::V0.

## Test::Deep — the piece you actually cannot replace

Neither Test::More nor Test2::V0 ships a structural matcher worth using for real data. `is_deeply` is exact equality on a tree: useful, but it forces you to construct a full expected structure for every assertion, and its diffs on a five-level hash are painful to read.

Test::Deep's synopsis shows the escape hatch:

```perl
use Test::More tests => $Num_Tests;
use Test::Deep;

cmp_deeply(
  $actual_horrible_nested_data_structure,
  $expected_horrible_nested_data_structure,
  "got the right horrible nested data structure"
);

cmp_deeply(
  $object,
  methods(name => "John", phone => "55378008"),
  "object methods ok"
);

cmp_deeply(
  \@array,
  [$hash1, $hash2, ignore()],
  "first 2 elements are as expected, ignoring 3"
);
```

Three matchers carry most of the weight in practice. `ignore()` skips a value entirely — indispensable for timestamps and generated IDs. `bag(...)` asserts the same elements in any order, which is what you usually mean when comparing a set of rows from a database. `array_each(...)` applies a matcher to every element, so ten near-identical records become one line of expectation. There is also `methods(...)` for asserting on an object's interface rather than its internals, which is the correct way to test most OO Perl.

Test::Deep is additive: it wraps `cmp_deeply` around the harness you already use. That makes it the lowest-risk adoption in this entire comparison — one `use` line, no migration, immediate readability win.

## TAP, `prove` and parallelism

All three ultimately emit TAP, and `prove` is the runner you will use either way:

```bash
# run everything in t/, verbose, with a shared library path
prove -lv -Ilib t/

# run 8 test files in parallel
prove -j8 -Ilib t/
```

Parallelism is the sharpest practical difference. `prove -j8` forks and runs separate *files* concurrently, which works for any framework. The difference is what happens inside a file: with Test2, concurrent assertions post events to the hub and are aggregated correctly; with Test::More, interleaved output from threads or forked children corrupts the TAP stream. If your suite spawns workers and asserts from them, that is a Test2 problem solved by design rather than by discipline.

For CI output, TAP is easy to convert. `prove --harness TAP::Harness::JUnit` produces JUnit XML for Jenkins or GitLab, and our [test result aggregation comparison](../2026-05-08-self-hosted-test-result-aggregation-allure-reportportal-jenkins-guide/) covers the reporting side once you are emitting machine-readable results.

## Migration pitfalls

**1. One conflicting export breaks the whole file.** Moose's `meta()` versus Test2::V0's `meta()` is the classic case. Import with `'!meta'` and use `meta_check()`.

**2. `use_ok` and `require_ok` are discouraged in Test2.** They load modules at compile time in ways that interact badly with the event hub. Prefer a plain `use Module;` at the top of the test file.

**3. Fixed plans and `done_testing` do not mix.** Pick one per file. If you keep a numeric plan, changing assertions mid-file means changing the number, and a mismatch fails the whole run.

**4. `is_deeply` is exact equality, not subset matching.** Blessing a hash into an object changes the comparison. Either compare `$obj->as_hashref` or use Test::Deep's `methods()`.

**5. Subtest failures must be asserted to fail the parent.** In both frameworks, a failed subtest marks the parent test as failed automatically — but if you catch exceptions inside a subtest, make sure you re-`fail()` rather than swallowing them.

**6. Encoding.** Non-ASCII diagnostics render as mojibake unless the test file and the output handle agree. Test2::V0's `utf8` pragma exists exactly for this.

**7. Test order dependence.** Global state leaks between files run in the same process unless each file is isolated. `prove` forks per file by default, which hides the problem until someone runs a single file after another in the same interpreter.

**8. Do not rewrite a passing suite for style.** Migrating 5,000 assertions to Test2::V0 buys you better diffs and future tooling; it does not fix bugs. Migrate the files you are already touching.

If your Perl stack is web-facing, the [Perl web framework comparison](../2026-08-01-perl-web-frameworks-mojolicious-dancer2-catalyst-comparison/) covers how these frameworks wire up their own test harnesses. For teams pushing test quality further, the [property-based testing guide](../2026-05-04-self-hosted-property-based-testing-hypothesis-fastcheck-proptest-guide/) explains the generate-instead-of-enumerate approach that complements all three of these tools.

## FAQ

**Is Test2::V0 a replacement for Test::More?**
Effectively yes — it exports a superset of the common assertions and is the recommended stack for new code. It is not a drop-in replacement for every edge case, and it is not in core, so existing suites can stay on Test::More indefinitely without being wrong.

**Do I need Test::Deep if I use Test2::V0?**
If you compare nested data structures and want readable, flexible expectations, yes. Test2::V0's `is_deeply` is exact equality. Test::Deep adds `ignore()`, `bag()`, `array_each()` and `methods()`, none of which have equivalents in core.

**Can I run the two frameworks in the same project?**
Yes. They coexist file by file, and Test2 provides a compatibility layer for Test::More-based tools. Migrate incrementally: convert the file you are already editing, verify TAP output, move on.

**Why does my suite fail with "planned 23 tests but ran 24"?**
You have a fixed plan and added an assertion. Delete the number and call `done_testing()` at the end of the file.

**Does Test2 support parallel test execution?**
Yes. Test2's event hub is designed to aggregate results across concurrent execution, which is why it is the recommended stack for suites that fork workers or use threading. Test::More's globals make that unsafe inside a single file.

**What is the minimum viable modern Perl test file?**
`use Test2::V0;` — then assertions, then `done_testing;`. Four lines including the shebang, no plan arithmetic, full diagnostics.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Perl Testing in 2026: Test2::V0 vs Test::More vs Test::Deep — Which Stack Should You Run?",
  "description": "Practical comparison of Perl testing stacks in 2026: Test2::V0, Test::More and Test::Deep, with real synopsis code, TAP output, parallelism and migration pitfalls.",
  "datePublished": "2026-10-20",
  "dateModified": "2026-10-20",
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
