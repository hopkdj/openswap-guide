---
title: "Unity vs Criterion vs Check in 2026: The Honest C Unit Testing Guide"
date: "2026-09-06"
tags: ["c", "unit-testing", "embedded", "developer-tools", "testing"]
draft: false
---

Every C developer knows the feeling: your code compiles, the demo works, and then a refactor silently corrupts a buffer that only misbehaves on someone else's machine. C has no runtime safety net, which is exactly why a serious unit testing framework matters more here than in almost any other language. But the C testing ecosystem splits into three very different philosophies: **Unity** (5,368 stars) is the embedded-first framework built around a single file you drop into any toolchain, **Criterion** (2,300 stars) is the modern xUnit-style framework that removes the boilerplate entirely, and **Check** (1,174 stars) is the two-decade-old classic that runs every test in its own forked process.

Pick the wrong one and you will fight your test harness instead of your code. Pick the right one and tests become the fastest feedback loop in your project.

## TL;DR: Quick Verdict

If you target **microcontrollers, firmware, or any resource-constrained environment**, use Unity with its Ceedling build companion — it runs anywhere a C compiler runs, including 8-bit targets, and its mocking library (CMock) makes hardware dependencies testable on a host machine. If you write **C or C++ for desktop, servers, or libraries and hate test boilerplate**, use Criterion — tests self-register, crashes are caught per-test, and you never write a main function. If you maintain **legacy autotools projects or need strict POSIX-style isolation**, Check is still a rock-solid choice, especially since its fork-per-test model catches segfaults that in-process frameworks miss entirely.

## Unity vs Criterion vs Check: Feature Comparison

| Feature | Unity (ThrowTheSwitch) | Criterion (Snaipe) | Check (libcheck) |
|---|---|---|---|
| GitHub stars | 5,368 | 2,300 | 1,174 |
| License | MIT | MIT | LGPL-2.1 |
| Last push (2026) | Aug 25 | Sep 5 | Jul 13 |
| C standard target | Any (C89+) | C99 / C++11 | C89+ (variadic macros warn under strict C90) |
| Embedded/MCU support | First-class | No | No |
| Test registration | Manual (`RUN_TEST`) or generated runner | Automatic on declaration | Manual (`tcase_add_test`) or `checkmk` generator |
| Needs a `main()` | Yes (or generate_test_runner.rb) | No (default entry point) | Yes |
| Process isolation per test | No | Yes | Yes (fork-based) |
| Catches segfaults/signals as failures | No | Yes | Yes |
| Parameterized tests | No (loop in one test) | Yes (theories/parameters) | No |
| Mocking support | Via CMock | External | External |
| TAP output | No | Yes | Partial (via `--tap` in newer releases) |
| C++ support | Via C linkage | Native unified API | Via C linkage |

## Decision Matrix: Which Framework Should You Pick?

| Use Case | Recommended Framework | Why |
|---|---|---|
| Firmware for STM32/AVR/ESP32 or any bare-metal target | Unity | Single C file + two headers compiles with any cross toolchain; no libc dependency assumptions |
| Unit-testing host-side logic of embedded code on your laptop | Unity + Ceedling/CMock | Ceedling wires Unity into a Ruby-based build with mocks auto-generated from headers |
| New desktop/server C or C++ project, want zero ceremony | Criterion | Tests self-register, no `main()`, parametrized tests built in, crashes reported per test |
| CI pipeline needs machine-readable output | Criterion | Native TAP output plus JSON report hooks |
| Legacy autotools project or GNOME-ecosystem code | Check | The de facto standard in autotools land; integrates with `make check` |
| You need to prove a segfaulting function fails cleanly, not nuke the suite | Criterion or Check | Both isolate tests in child processes |

## Unity: The Embedded Standard

Unity was created in 2007 by Mike Karlesky, Mark VanderVoord, and Greg Williams (the ThrowTheSwitch team) specifically because embedded developers needed a test framework that behaves identically on a host PC and on a 16 MHz microcontroller. The entire core is **one C file and a pair of headers** — you add it to your build the same way you add any source file, whether you use Make, CMake, IAR, or Keil.

Test functions take no arguments, return nothing, and all accounting is handled internally. A typical test file looks like this (from the official getting-started guide):

```c
#include "unity.h"
#include "file_to_test.h"

void setUp(void) {
    // set stuff up here
}

void tearDown(void) {
    // clean stuff up here
}

void test_function_should_doBlahAndBlah(void) {
    //test stuff
}

void test_function_should_doAlsoDoBlah(void) {
    //more test stuff
}

// not needed when using generate_test_runner.rb
int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_function_should_doBlahAndBlah);
    RUN_TEST(test_function_should_doAlsoDoBlah);
    return UNITY_END();
}
```

Unity's assertion macros read like a cheat sheet: `TEST_ASSERT_TRUE(condition)`, `TEST_ASSERT_EQUAL_INT32(expected, actual)`, `TEST_ASSERT_EQUAL_HEX8(...)`, string and memory comparisons (`TEST_ASSERT_EQUAL_STRING`, `TEST_ASSERT_EQUAL_MEMORY`), and `TEST_FAIL()` for unconditional failure. The typed integer variants are what make it shine on embedded targets where `int` size changes between platforms — you explicitly assert on `INT32` or `UINT16` widths so a test means the same thing on a PC and on a Cortex-M.

**The real productivity unlock is Ceedling**, ThrowTheSwitch's build tool. It manages Unity + CMock (automock generation from your headers) + Ceedling test runners, so a `rake`-style workflow generates mocks for hardware peripherals and runs tests on the host with zero manual `main()` bookkeeping. That combination — Unity core, CMock mocks, Ceedling orchestration — is why embedded teams consistently rank it the default choice. As of September 2026 the project remains very active (last push August 25, 2026), with the API stable for years.

## Criterion: Modern Ergonomics Without the Boilerplate

Criterion's stated philosophy is KISS: most C test frameworks force you to create a main, register suites, register tests inside suites, then call the right functions. Criterion instead gives you **automatic test registration and a default entry point** — you never write `main()` unless you need special handling. It is C99 and C++11 compatible with a unified interface, so the same header works for both languages.

From the official sample (`samples/asserts.c` in the repository):

```c
#include <criterion/criterion.h>
#include <criterion/new/assert.h>

Test(asserts, base) {
    cr_assert(true);
    cr_expect(true);

    cr_assert(true, "Assertions may take failure messages");

    cr_assert(true, "Or even %d format string %s", 1, "with parameters");

    cr_expect(false, "assert is fatal, expect isn't");
    cr_assert(false, "This assert runs");
    cr_assert(false, "This does not");
}

Test(asserts, string) {
    cr_assert(zero(str, ""));
    cr_assert(not (zero(str, "foo")));

    cr_assert(eq(str, "hello", "hello"));
    cr_assert(ne(str, "hello", "olleh"));
}

Test(asserts, native) {
    cr_assert(eq(i32, 1, 1));
    cr_assert(ne(i32, 1, 2));
    cr_assert(lt(i32, 1, 2));
}
```

Two design decisions make Criterion stand out. First, **`cr_assert` is fatal while `cr_expect` is not** — a failed `cr_assert` aborts just that test (in its own process), while `cr_expect` records the failure and keeps going. This lets you write "soft" checks that collect every problem in one run. Second, **every test executes in an isolated process**, so a segfault, assertion trap, or `SIGKILL` in one test is reported as that test's failure and the rest of the suite keeps running. The newer fluent API (`eq(i32, ...)`, `zero(str, ...)`, `gt`, `ge`, `lt`, `le`) reads closer to a spec language than classic macro asserts.

Installation is genuinely cross-platform: `apt-get install libcriterion-dev` on Debian/Ubuntu, `pacman -S criterion` on Arch, `brew install criterion` on macOS, `pkg install criterion` on FreeBSD, plus official binary releases for Linux x86_64. Parameterized tests, theories, real-time progress hooks, and TAP output round out the feature set. Version 2.4.x is current, with the last push on September 5, 2026 — the most actively developed framework of the three.

## Check: The Battle-Tested Classic

Check has been around since 2001 (Arien Malec's original work) and is the framework behind countless GNOME-era C projects. Its defining feature is that **tests run in a separate address space**, so Check catches both assertion failures *and* code errors that cause segmentation faults or other signals — a capability it shares with Criterion but not with in-process frameworks.

The canonical example from the official tutorial (the "Test Infected" Money example) shows the model:

```c
#include <check.h>
#include "money.h"

START_TEST(test_money_create)
{
    money_t *money = money_create(5, "USD");
    ck_assert_int_eq(money_amount(money), 5);
    ck_assert_str_eq(money_currency(money), "USD");
    money_free(money);
}
END_TEST
```

Tests are grouped into `TCase` objects, which join a `Suite`, and a `SRunner` executes everything:

```c
Suite *money_suite(void) {
    Suite *s = suite_create("money");
    TCase *tc = tcase_create("core");
    tcase_add_test(tc, test_money_create);
    suite_add_tcase(s, tc);
    return s;
}

int main(void) {
    Suite *s = money_suite();
    SRunner *sr = srunner_create(s);
    srunner_run_all(sr, CK_NORMAL);
    int failed = srunner_ntests_failed(sr);
    srunner_free(sr);
    return (failed == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
```

Assertions come in tiers: `ck_assert(expr)` for plain booleans, `ck_assert_int_eq`/`ck_assert_str_eq` for typed equality, `ck_assert_msg` for printf-style failure messages, and `ck_abort`/`ck_abort_msg` to fail unconditionally. Because Check was born in the autotools era, it integrates unusually well with classic build systems: `make check` runs the suite and logs per-test results, and the `checkmk` tool generates test stubs from specially-commented C files. Installation follows the same tradition (`autoreconf --install && ./configure && make && make install`) although modern CMake builds work too. The project still receives maintenance (last push July 13, 2026) and its LGPL-2.1 license is the one to double-check if you statically link into proprietary software.

## Real-World Pitfalls and Migration Notes

- **`cr_assert` vs `cr_expect` semantics will bite you.** In Criterion, a fatal assert aborts only the current test, not the process — but if you migrated from Unity habits where every failure is recorded, your "soft" checks may silently hide cascading failures. Decide per-suite whether a failure should halt immediately.
- **Unity is not the Unity game engine.** Searching for "Unity testing framework" returns the game engine first. The C framework lives at `ThrowTheSwitch/Unity` on GitHub, and its companion tools are Ceedling (build) and CMock (mocking). Verify you are cloning the right repository.
- **Manual `RUN_TEST` lists rot.** With Unity, forgetting to add a test to `main()` means it silently never runs. Use `generate_test_runner.rb` or Ceedling so the runner is generated from your test file, or add a CI check that greps for test functions missing a `RUN_TEST` call.
- **Check's fork-per-test model has real overhead.** Each test costs a process spawn, so thousands of trivial tests run slower than in-process frameworks. If your suite is huge and fast, Criterion's isolation is the same safety with less ceremony; if you need raw throughput, in-process testing may be the pragmatic trade-off.
- **Strict C90 compilers choke on variadic macros.** Check's `check.h` uses variadic macros and GCC emits warnings under `-std=c90` unless you pass `-Wno-variadic-macros`. Keep your test files on C99 or newer.
- **LGPL static linking.** Check is LGPL-2.1. Dynamically linking is unproblematic, but static linking into a closed-source product has obligations — Unity (MIT) or Criterion (MIT) remove the question entirely.
- **Embedded cross-compilation is a hard filter.** If your code must be tested on-target or with a vendor toolchain (IAR, Keil, arm-none-eabi-gcc), only Unity realistically supports that. Criterion and Check assume a hosted POSIX-ish environment.
- **C++ projects:** Criterion has a native unified C/C++ API; Unity and Check need `extern "C"` handling and lose some ergonomics. For mixed C/C++ codebases, Criterion is the least friction.

For a deeper look at adjacent C-ecosystem tooling, see our [embedded C HTTP library comparison](../2026-09-04-embedded-c-http-libraries-mongoose-civetweb-libmicrohttpd/). If you are evaluating testing frameworks in other languages, our [OCaml testing frameworks comparison](../2026-08-01-ocaml-testing-libraries-ounit-alcotest-qcheck/) and the [Java testing frameworks guide](../2026-07-29-java-testing-frameworks-junit5-testng-spock-guide/) cover the same decision from those ecosystems' perspectives. For mocking-focused workflows, our [Python pytest plugins article](../2026-07-26-python-pytest-plugins-mock-cov-xdist-timeout-asyncio/) shows what a batteries-included plugin ecosystem looks like when you outgrow a bare framework.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Unity vs Criterion vs Check in 2026: The Honest C Unit Testing Guide",
  "description": "Compare the three dominant C unit testing frameworks: Unity for embedded, Criterion for modern host-based projects, and Check for legacy autotools codebases. Feature tables, real code examples, and migration pitfalls.",
  "datePublished": "2026-09-06",
  "dateModified": "2026-09-06",
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

**Which C unit testing framework is best for embedded development?**
Unity. Its core is a single C file and two headers that compile with any embedded toolchain including IAR, Keil, and arm-none-eabi-gcc. Combined with Ceedling for builds and CMock for auto-generated mocks of hardware peripherals, it is the de facto standard for microcontroller firmware testing.

**Does Criterion require me to write a main function?**
No. Criterion provides a default entry point and automatically registers tests when they are declared with the `Test()` macro. You only write a custom `main()` for special handling such as custom reporters or global setup.

**How do Criterion and Check isolate tests from crashes?**
Both run each test in a separate child process. If a test dereferences a bad pointer or hits an assertion trap, that test is marked failed with the signal reported, and the remaining tests continue running normally.

**Is Check still maintained in 2026?**
Yes. The libcheck project received its last push on July 13, 2026, and remains the standard choice in autotools-based and GNOME-ecosystem projects. Development is slower than Criterion's, but the framework is mature and stable.

**Can I use Unity to test C++ code?**
Unity is written for C, though it can be used from C++ with `extern "C"` handling. If you write mixed C/C++ code, Criterion is the better fit because its unified API supports C99 and C++11 through the same header.

**Which framework supports parameterized tests?**
Criterion supports parameterized tests and theories natively. Unity and Check have no built-in parameterization — you loop inside a single test or generate multiple test registrations with `checkmk`.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
