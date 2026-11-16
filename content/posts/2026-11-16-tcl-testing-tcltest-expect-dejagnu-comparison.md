---
title: "Tcl Testing in 2026: tcltest vs Expect vs DejaGnu — Which Harness Fits Your Legacy Stack?"
date: "2026-11-16"
tags: ["tcl", "testing", "automation", "legacy-systems", "developer-tools"]
draft: false
cover: "/img/screenshots/tcl-testing-logo.jpg"
description: "tcltest, Expect and DejaGnu compared for testing Tcl code and interactive systems: real code, real configure options, Tcl 9 migration notes and the traps of an unmaintained Expect mirror."
---

Tcl is not a hobby language. It is embedded in EDA toolchains, network device automation, storage arrays, and the test suites of projects as widely deployed as SQLite. That means a very specific career moment keeps repeating: you inherit 40,000 lines of Tcl, nobody remembers how the test suite is supposed to run, and `make test` prints either nothing or a wall of failures with no summary.

There are three legitimate answers in 2026 — **tcltest** (the official harness shipped with Tcl), **Expect** (Tcl's black-box automation engine), and **DejaGnu** (GNU's Tcl-based test framework used by GCC, binutils and gdb). They solve different problems, and using the wrong one is why so many Tcl suites are quietly abandoned.

## TL;DR — Quick Verdict

**Use `tcltest` for unit-testing Tcl procs. Use Expect when the thing under test is another process talking over a terminal. Use DejaGnu only if you are already inside a GNU toolchain or need a `runtest`-style harness at GCC scale.**

- **Your tests are `proc`s, data structures or parsers?** `tcltest`. It ships with every Tcl install, has constraints for platform-specific tests, and produces a pass/fail summary when you call `cleanupTests`.
- **You need to drive `ssh`, `telnet`, a CLI, or a login prompt?** Expect. It is the only tool here that models "send this, wait for that pattern, then assert".
- **You are testing a compiler, linker, or a tool that must fail with a specific diagnostic?** DejaGnu's `pass`/`fail`/`xfail` model with `.exp` files is the established pattern — and it is heavy.

The trap in 2026 is not picking the wrong framework. It is downloading the **unmaintained Expect repository** instead of the Tcl 9 port.

## The Three Harnesses Compared

| Dimension | tcltest | Expect | DejaGnu |
|---|---|---|---|
| Role | Unit test harness in Tcl core | Interactive process automation | Full test framework on top of Expect |
| Where it lives | Tcl core (`tcltk/tcl`) | `tcltk-depot/expect` (Tcl 9 port) | GNU DejaGnu, `runtest` |
| GitHub stars | **848** (`tcltk/tcl`) | **12** (`tcltk-depot/expect`) | Not on GitHub as a first-class repo |
| Last push | Nov 16, 2026 | Oct 8, 2026 | Infrequent GNU releases |
| Test file shape | `.test` files, `test` command | Any Tcl script with `spawn`/`expect` | `.exp` files driven by `runtest` |
| Assertion style | `test name desc -body {} -result {}` | Pattern match on process output | `pass` / `fail` / `xfail` inside `expect` |
| Constraint system | **Yes** (`-constraints`, `testConstraint`) | Manual (`if {[info exists env(CI)]}`) | Yes, via target boards |
| Isolation | Separate interpreter per file (unless `-singleproc`) | One spawned process per test | Separate `runtest` invocation |
| Result summary | `cleanupTests` prints totals | You print it | `runtest` summary + `.sum`/`.log` files |
| Learning curve | An hour | An afternoon | A day, minimum |
| Best fit | Tcl libraries and scripts | CLI, SSH, device and prompt-driven tests | Compiler / toolchain suites |

That 12-star count on the Expect port is not a red flag about the software — it is a red flag about **discoverability**. Expect has been infrastructure for three decades; the Tcl 9 port is simply new enough that its repository still looks tiny.

## Scenario Decision Matrix

| Your situation | Pick | Why |
|---|---|---|
| Testing a Tcl library's procs | tcltest | Native, zero install, summary output |
| Test must be skipped on Windows only | tcltest + constraints | `testConstraint` is built for this |
| Verifying an interactive CLI's prompts | Expect | Only tool that can wait for patterns |
| Automating SSH into a device and asserting output | Expect | `spawn ssh`, `expect -re`, `send` |
| GCC-style suite with expected diagnostics | DejaGnu | `.exp` files + `runtest` |
| CI runs on Alpine, minimal image | tcltest | Ships with `tcl` package |
| You need machine-readable XML results | None natively | Wrap stdout in your CI's parser or add a reporter |

## tcltest — the Harness That Ships With Tcl

`tcltest` is part of the Tcl core distribution. You load it as a package, import the commands, declare tests, and call `cleanupTests` at the end — that last call is what prints the summary and returns a proper exit status.

```tcl
# tests/backoff.test
package require tcltest 2.5
namespace import ::tcltest::*

configure -testdir [file dirname [file normalize [info script]]] \
          -verbose {pass error} \
          -match glob

proc computeBackoff {attempt} {
    if {$attempt <= 0} {
        error "attempt must be positive"
    }
    set delay [expr {100 * (1 << ($attempt - 1))}]
    if {$delay > 30000} { return 30000 }
    return $delay
}

test backoff-1.1 "exponential growth" -body {
    computeBackoff 1
} -result 100

test backoff-1.2 "caps at thirty seconds" -body {
    computeBackoff 20
} -result 30000

test backoff-1.3 "rejects zero attempts" -body {
    computeBackoff 0
} -returnCodes error -result "attempt must be positive"

cleanupTests
```

Run it:

```bash
tclsh tests/backoff.test
# or, to run every .test file in a directory:
tclsh <<'EOF'
package require tcltest
namespace import ::tcltest::*
configure -testdir tests -file *.test -verbose {pass error}
runAllTests
cleanupTests
EOF
```

The short positional form from the official man page also works, which is what most legacy suites use:

```tcl
test backoff-2.1 {positional form} {
    computeBackoff 4
} 800
```

Two features make `tcltest` worth learning properly:

**Constraints.** Platform or dependency-specific tests get excluded cleanly instead of failing:

```tcl
testConstraint hasOpenssl [expr {![catch {package require tls}]}]

test tls-1.1 "TLS handshake available" -constraints hasOpenssl -body {
    package present tls
} -result 1
```

**Configuration over rewriting.** The `configure` command accepts a long list of options documented in `tcltest.n`: `-testdir`, `-file`, `-notfile`, `-match`, `-skip`, `-constraints`, `-limitconstraints`, `-singleproc`, `-tmpdir`, `-preservecore`, `-verbose`, `-asidefromdir`, `-relateddir`, `-load`, `-loadfile`, `-debug`, `-errfile`, `-outfile`, and `-iterations`. That means you can make a 15-year-old suite runnable in CI **without editing a single test**.

**The one thing that breaks suites:** if `cleanupTests` is never called, you get no summary and the process exits 0 even when tests failed. Grep your inherited suite for it first — a missing `cleanupTests` is the single most common reason a "green" Tcl build is actually red.

## Expect — Testing Things That Talk Back

Expect is Tcl extended with process control: `spawn` starts a program on a pseudo-terminal, `expect` waits for a pattern, `send` writes to it. If your test subject is a CLI, an SSH session, a router prompt, or a `passwd` dialogue, no unit test harness can reach it.

```tcl
#!/usr/bin/env expect
# tests/login.exp — verify the CLI prompts then reject a bad password

set timeout 10
log_user 0

spawn ssh -o StrictHostKeyChecking=no tester@127.0.0.1
expect {
    -re "(P|p)assword:" { send "wrongpass\r" }
    timeout { puts "FAIL: no password prompt"; exit 1 }
}

expect {
    -re "(denied|invalid)" { puts "PASS: bad password rejected" }
    eof { puts "FAIL: session closed before rejection"; exit 1 }
    timeout { puts "FAIL: no rejection message"; exit 1 }
}

close
exit 0
```

Practical patterns that make Expect suites survivable:

```tcl
# 1. Never let a default timeout decide your CI result silently
set timeout 15

# 2. Keep transcript noise out of logs, turn it on for debugging only
log_user 0
# log_user 1

# 3. Assert on a regexp, not on a fixed string, when output is device-specific
expect -re {Uptime:\s+(\d+)\s+days} {
    set days $expect_out(1,string)
    if {$days < 1} { puts "FAIL: device rebooted"; exit 1 }
}

# 4. Always drain to EOF before exiting, or you test a truncated interaction
expect eof
```

**The 2026 pitfall:** the historical Expect repository at `core.tcl-lang.org/expect` carries an explicit notice that it is **no longer maintained**, with the updated version supporting both Tcl 8.6 and Tcl 9 living in the `tcltk-depot` organization. If you `apt install expect` on a modern distro you may get either build; pin the source or vendor the Tcl 9 port, because the Tcl 9 changes to channel handling and string internals hit Expect harder than they hit ordinary scripts.

## DejaGnu — the Framework Behind GCC's Test Suite

DejaGnu wraps Expect into a full test framework: a driver called `runtest` reads `.exp` files, runs them against a "target board", and emits `.sum` and `.log` files plus a pass/fail/xfail tally. It is how GCC, binutils and gdb are tested, which means it is battle-tested at a scale nothing else in this article reaches.

A minimal `.exp` file looks like this:

```tcl
# testsuite/mytool.exp
set test "mytool prints usage on bad flag"

send "mytool --nonsense\r"
expect {
    -re "usage:" { pass $test }
    timeout     { fail "$test (timeout)" }
    eof         { fail "$test (exited without usage)" }
}
```

Run it:

```bash
runtest --tool mytool --srcdir ./testsuite
```

Real DejaGnu suites add machinery that is genuinely useful at scale: `xfail` for known-broken behaviour, target board descriptions for cross-compiled hardware, `dg-require-effective-target`-style guards in GCC's layer, and per-run summaries that a buildbot can parse.

**Honest assessment:** if you are not already in a GNU toolchain, DejaGnu's setup cost — site.exp, board files, srcdir layout, `runtest` version matching — will exceed the value you get. It is the right tool for "test a compiler on three architectures", and the wrong tool for "test my 600-line Tcl utility".

## Pitfalls, Migration Notes and Performance Traps

- **Missing `cleanupTests`** means no summary and a zero exit code even with failures. Add it, or wrap your runner so a failed count aborts CI.
- **`-singleproc 1` hides state leakage.** The default is a fresh interpreter per test file, which is slow but isolates globals. If someone added `-singleproc` for speed, cross-test contamination becomes possible — the fastest fix is usually to reset globals in a `-setup` script rather than to remove the flag.
- **Core dumps fill disks.** `-preservecore` keeps core files for failing tests; on a loop that generates thousands. Set it to `0` or `2` deliberately, and point `-tmpdir` at a scratch volume.
- **Constraint names with spaces need braces.** `-constraints {unix hasOpenssl}` is a list; `-constraints unix hasOpenssl` passes the second word as the body argument and produces a bewildering error.
- **Expect's `timeout` is not a test failure by itself.** `expect` returns on timeout just like it returns on a match. Every `expect` block needs an explicit `timeout` branch, or your test passes when the program hangs.
- **`log_user 0` hides the evidence you need.** When a test fails intermittently, flip it back on and capture the transcript to an artefact; Expect failures are almost always diagnosable from the exact bytes that arrived.
- **Tcl 8.6 vs 9.x differences bite in channel code.** `fconfigure`-era code and binary translations behave differently; run the suite under both interpreters before you claim Tcl 9 support.

## Why Legacy Test Suites Are Worth Reviving

The economics of Tcl are unusual: the code is often in a device, an EDA flow, or a build system that will outlive three generations of web frameworks. That makes the test suite the most valuable documentation in the repository — and the cheapest insurance you can buy.

The good news is that reviving one costs almost nothing if the harness is `tcltest`: install `tcl`, run the suite, fix the missing `cleanupTests`, and add constraints for the platforms you no longer have. No framework migration, no new dependency, no rewriting assertions. Expect and DejaGnu suites are harder to revive, but their value is concentrated in the tests that drive real processes — the ones a unit test can never replace.

For adjacent reading, our [Tcl web stacks comparison](../2026-09-16-tcl-web-stacks-naviserver-apache-rivet-openacs-comparison/) covers the server side of the same ecosystem, the [GNU COBOL toolchain review](../2026-09-14-gnucobol-vs-superbol-vs-cobol-check-open-source-cobol-toolchain/) is a parallel case study in modernising legacy-language CI, and our [Erlang testing frameworks guide](../2026-09-07-erlang-testing-frameworks-eunit-commontest-proper-comparison/) shows how another long-lived ecosystem structures the same trade-offs.

## FAQ

**Is tcltest still maintained in 2026?**
Yes. It ships with the Tcl core, and the Tcl core repository is actively pushed to — the last push was November 16, 2026, with 848 stars on the GitHub mirror. The `tcltest` package version you require (`2.5` or newer) has been stable for years, which is a feature for legacy suites: your tests will not break because the harness changed.

**What is the difference between tcltest and Expect?**
`tcltest` tests Tcl code inside the interpreter: you call a proc and compare the result. Expect tests *other programs* through a pseudo-terminal: you spawn a process, wait for a pattern, send input, and assert on what comes back. If your test subject needs a prompt or a login, Expect is the only option of the two.

**Should I use DejaGnu for a normal Tcl project?**
No, unless you are already inside a GNU toolchain. DejaGnu's value is a `runtest` driver, target boards and `.sum` summaries at compiler-suite scale. For a regular Tcl library, `tcltest` covers the same assertions with none of the setup.

**Why does my tcltest run exit successfully even though tests failed?**
Because `cleanupTests` was never called. That command collects the failure count, prints the summary, and sets the process exit status. Without it, `tclsh` exits 0 regardless of failures — the most common silent failure in inherited Tcl suites.

**Can I get JUnit XML out of tcltest or DejaGnu?**
Neither produces JUnit XML natively. `tcltest` writes plain-text summaries and optionally an output file; DejaGnu writes `.sum` and `.log` files per run. Most teams wrap the runner in a small script that parses the summary line and emits XML, or let their CI treat the summary as plain log output.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Tcl Testing in 2026: tcltest vs Expect vs DejaGnu — Which Harness Fits Your Legacy Stack?",
  "description": "tcltest, Expect and DejaGnu compared for testing Tcl code and interactive systems: real code, configure options, Tcl 9 migration notes and maintenance traps.",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
