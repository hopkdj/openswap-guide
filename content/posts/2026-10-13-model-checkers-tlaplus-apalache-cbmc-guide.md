---
title: "TLA+ vs Apalache vs CBMC in 2026: Which Model Checker Should You Actually Use?"
date: "2026-10-13"
tags: ["formal-verification", "model-checking", "developer-tools", "testing"]
draft: false
cover: "/img/screenshots/osg-tla-editor.jpg"
---

Some bugs are invisible to every test you will ever write. A distributed lock that passes code review can still lose a message under one interleaving in ten million, and no amount of unit testing explores the schedules your production cluster will invent at 3 a.m. Model checkers exist to attack exactly that class of bug — by enumerating the behaviours your design allows instead of sampling a handful of them.

The confusion is that "model checker" describes two different jobs: proving things about a **design** written as a specification, and proving things about **source code** written in C. TLA+ and Apalache do the first. CBMC does the second. Buying one when you need the other wastes a sprint.

**TL;DR:** Use **TLA+ with TLC** when you want to find design-level bugs in concurrency protocols and algorithms — it is the most widely adopted option, MIT licensed, and its upstream repository saw commits on **13 October 2026**. Add **Apalache** when the same specification has to be checked symbolically, because TLC enumerates states and Apalache reasons over them. Use **CBMC** when your artefact is C or C++ source and your worries are memory safety, bounds, overflow and assertion failures. If you can only adopt one, pick TLA+ — it is the only one of the three with a mainstream audience, and the tooling around it keeps improving.

## Three Tools, Two Jobs

| Dimension | TLA+ (TLC) | Apalache | CBMC |
|---|---|---|---|
| What it checks | A specification written in TLA+ / PlusCal | A specification written in TLA+ or Quint | C and C++ source code |
| Method | Explicit-state enumeration | **Symbolic**, constraint-based | **Bounded** model checking with loop unwinding |
| Upstream stars | **3,116** | **607** | **1,139** |
| Last upstream commit | **2026-10-13** | **2026-10-12** | **2026-10-12** |
| Licence | MIT | Apache-2.0 | Open source, BSD-style (see the repository LICENSE) |
| Official container image | Not published in the repo | **`ghcr.io/apalache-mc/apalache`** | **`diffblue/cbmc` on Docker Hub** |
| Runtime requirement | Java 11+ | Java or Docker | Native binary, no runtime |
| Best at | Protocol design, distributed algorithms, spec-level invariants | Parameterised specs where enumeration blows up | Memory safety, overflow, bounds, assert violations in C/C++ |

### Decision Matrix: Pick One in Ten Seconds

| Your situation | Pick | Why |
|---|---|---|
| You are designing a consensus, locking or replication protocol | **TLA+ / TLC** | Small state spaces and design bugs are exactly what explicit-state checking nails |
| Your spec has parameters that make the state space explode | **Apalache** | Symbolic checking reasons about classes of states instead of enumerating them |
| You must verify a C function that parses untrusted input | **CBMC** | It works directly on the source and produces a concrete counterexample trace |
| You want a certificate that memory is not out of bounds | **CBMC** | Bounds and overflow checks are its native checks |
| You want to verify a Rust, Go or Python service | **TLA+ or Apalache** | CBMC targets C/C++; for other languages model the design, not the code |
| You have to run checks inside a container pipeline | **Apalache or CBMC** | Both publish official images; TLA+ ships a jar you can bake into any image |

## TLA+: The Design-Level Workhorse

TLA+ is the specification language Leslie Lamport designed for reasoning about concurrent and distributed systems, and the repository we are looking at (`tlaplus/tlaplus`) hosts two things: the command-line tools and the Eclipse-based Toolbox IDE. It is **MIT licensed**, currently at **3,116 stars**, and it is the only tool in this comparison that your colleagues have probably already heard of.

The CLI is a single jar with several entry points. The upstream README documents them plainly:

```bash
# Get tla2tools.jar from the releases page, then:
export CLASSPATH=tla2tools.jar

java tla2sany.SANY -help   # the parser / semantic analyser
java tlc2.TLC -help        # the model checker
java tlc2.REPL             # interactive REPL
java pcal.trans -help      # PlusCal to TLA+ translator
java tla2tex.TLA -help     # TLA+ to LaTeX
```

Running `java -jar tla2tools.jar` is aliased to `tlc2.TLC`, so the shortest path to running a model check is one command and a spec file. Java 11 or newer is the only requirement.

Two practical notes that save hours. First, **PlusCal** is the pragmatic entry point: it looks like pseudocode and translates to TLA+, and `pcal.trans` is in the same jar. Second, the upstream README states the **Eclipse-based Toolbox GUI is currently unmaintained** and points to the **TLA+ VS Code extension** instead — so pick your editor accordingly rather than installing a legacy stack.

![The TLA+ Toolbox specification editor, from the upstream repository](/img/screenshots/osg-tla-tlc.jpg "TLA+ Toolbox GUI screenshot shipped in the tlaplus repository under general/docs/screenshots")

The characteristic failure mode is state explosion. TLC enumerates states, so a model with three integer counters ranging over a thousand values each is not a model — it is a denial-of-service attack on your laptop.

## Apalache: Symbolic Checking for the Same Specifications

Apalache is a **symbolic model checker for TLA+ and Quint**, and it is the reason you do not have to choose between "I wrote a TLA+ spec" and "I need symbolic reasoning". It is **Apache-2.0 licensed**, at **607 stars**, and it saw upstream commits on **12 October 2026**.

Its packaging is the friendliest of the three in a container pipeline, because the README documents an official image:

```bash
docker pull ghcr.io/apalache-mc/apalache:main
```

Where TLC walks the reachable state graph, Apalache encodes the problem as constraints and hands it to a solver, which changes the cost profile: parameterised specifications that make TLC choke can become tractable, while purely finite-state puzzles where enumeration is cheap may actually check faster in TLC. In practice, teams run both against the same spec — TLC for quick iteration during design, Apalache when the model must cover a family of configurations.

A Compose service for running Apalache against a directory of specs looks like this:

```yaml
services:
  apalache:
    image: ghcr.io/apalache-mc/apalache:main
    working_dir: /specs
    volumes:
      - ./specs:/specs
    command: ["check"]
```

Mount the spec directory, keep the invocation in `command`, and the same file that runs on a laptop runs in CI.

## CBMC: Bounded Model Checking of Real C and C++

CBMC ("C Bounded Model Checker") answers a completely different question: given **this source file**, can an assertion fail, an array be indexed out of bounds, a signed integer overflow, or a pointer be dereferenced after free? It is at **1,139 stars**, saw commits on **12 October 2026**, and is packaged more conventionally than a research tool usually is. The README lists both a distribution package and Homebrew:

```bash
# Debian/Ubuntu style install from the released package
#   download cbmc-x.y.deb from the releases page, then:
apt install cbmc-x.y.deb

# or, on macOS / Homebrew:
brew install cbmc
```

Docker users are not left out: the official **`diffblue/cbmc`** image on Docker Hub has pulled over **28,000** times and was last updated **24 June 2026**, so a verification step in CI can be a container instead of a package:

```yaml
services:
  cbmc:
    image: diffblue/cbmc:latest
    working_dir: /work
    volumes:
      - ./src:/work
    command: ["cbmc", "wrap.c"]
```

The "bounded" in the name is the honest caveat: CBMC verifies loops up to an unwinding bound you choose. If your parser loops `while (c != '\0')`, you must tell the tool how deep to look, and an assertion that only fails at iteration 100,000 will pass unless you raise the bound. That is a real limitation and a real strength — it turns "is this function safe?" into a knob you can reason about, and it is why CBMC also finds its way into unit-test generation workflows, where the counterexample trace becomes a test case.

## A Minimal TLA+ Spec and a Minimal CBMC Target

You can start today with a five-line TLA+ module:

```tla
---- MODULE Counter ----
EXTENDS Integers
VARIABLE x

Init == x = 0
Next == x' = x + 1
Spec == Init /\ [][Next]_x
====
```

That is enough to run `java -jar tla2tools.jar Counter.tla` and watch TLC explore the behaviour. From there, invariants are where the value appears: add a definition such as `Inv == x >= 0`, declare it in the config file, and TLC either confirms it across every reachable state or hands you a trace that violates it.

The equivalent smallest-useful CBMC target is a C file with an assertion nobody would write in a test suite:

```c
#include <assert.h>

int main(void) {
    unsigned int a = 0;
    unsigned int b = 3;
    assert(a - b < a);   /* unsigned wrap-around */
    return 0;
}
```

Run `cbmc wrap.c` and the checker reports the failing trace — the arithmetic wraps, the assertion is false, and you have a counterexample in seconds instead of a bug report in production.

## Which Bug Class Needs Which Tool

| Bug class | Best first tool | Notes |
|---|---|---|
| Two replicas disagree because of a missing interleaving | **TLA+ / TLC** | Design-level, smallest model that still reproduces the bug |
| Protocol that must hold for every ring size | **Apalache** | Symbolic checking avoids enumerating each size separately |
| Buffer overflow while parsing a crafted input | **CBMC** | Source-level, produces an input trace |
| Integer overflow in price arithmetic | **CBMC** | Overflow assertions are native checks |
| Deadlock in a job scheduler design | **TLA+ / TLC** | Model the scheduler, not the implementation |
| Spec drift: model says fine, code disagrees | **TLA+ or Apalache plus code review** | No model checker reads your implementation for you |

## Pitfalls That Cost Real Weeks

- **State explosion is the default outcome.** In TLC, keeping integers small is not an optimisation, it is the difference between a five-second check and an out-of-memory crash. Model a two-element set before you model a thousand-element one.
- **Bounded means bounded.** A green CBMC run proves your assertions hold up to the unwinding depth you passed. Raise the bound before you claim victory on loops that depend on input length.
- **Verifying a spec is not verifying your system.** A flawless TLA+ model of a protocol that your Go service implements differently proves nothing about the service. Treat the spec as the design contract and review the implementation against it.
- **Toolbox maintenance matters.** The upstream README is explicit that the Eclipse-based GUI is currently unmaintained; the VS Code extension is the supported path. Do not build a team workflow on the older tool.
- **Container tags drift.** Apalache's README documents `ghcr.io/apalache-mc/apalache:main`, and the CBMC image on Docker Hub was last updated in June 2026. Pin a digest in CI so a silent update does not change your verification results.
- **Model the smallest thing that can fail.** The most common wasted month is the specification that models the whole system instead of the three-message exchange where the bug lives.

For the theory-heavy end of this spectrum, our [proof assistants comparison covering Rocq, Coq, Lean 4 and Agda](../2026-09-13-proof-assistants-rocq-coq-lean4-agda-comparison/) explains when you want interactive proof rather than a model checker. If your constraints are arithmetic satisfiability rather than state exploration, the [SMT solver libraries comparison — Z3, CVC5, Yices, Boolector and Bitwuzla](../2026-06-22-smt-solver-libraries-z3-cvc5-yices-boolector-bitwuzla/) is the right starting point, and a runtime fuzzing harness such as those compared in our [AFL++ vs honggfuzz vs libFuzzer guide](../2026-04-25-aflplusplus-vs-honggfuzz-vs-libfuzzer-self-hosted-fuzzing-guide-2026/) catches the crashes that sit one layer below both.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "TLA+ vs Apalache vs CBMC in 2026: Which Model Checker Should You Actually Use?",
  "description": "A practical 2026 comparison of three open-source model checkers — TLA+ with TLC, Apalache and CBMC — covering explicit-state versus symbolic checking, real install commands, official container images and common pitfalls.",
  "datePublished": "2026-10-13",
  "dateModified": "2026-10-13",
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

**What is the difference between a model checker and a proof assistant?**
A model checker explores behaviours of a finite model and either finds a counterexample or reports that none exists within the checked scope. A proof assistant such as Rocq or Lean 4 lets you state a theorem and construct a machine-checked proof, which is far more general and far more work. Most engineering teams get more value per hour from model checking.

**Can TLC and Apalache check the same TLA+ specification?**
Yes. Both consume TLA+ specifications, and that is exactly why they work well together: TLC is an explicit-state model checker that enumerates reachable states, while Apalache is a symbolic model checker that encodes the problem as constraints. Run TLC for fast feedback during design and bring in Apalache when parameterised state spaces make enumeration impractical.

**Does CBMC verify C++ as well as C?**
CBMC's upstream repository is titled "C Bounded Model Checker" and it is used on C and C++ codebases. Its practical sweet spot is code where safety properties are expressible as assertions — bounds checks, overflow checks and pointer validity — rather than whole-program functional correctness.

**Do I need Docker to run these tools?**
No. TLA+ ships `tla2tools.jar` and only needs Java 11 or newer. CBMC has Homebrew and distribution packages. Docker is simply the most reproducible path: Apalache documents the official `ghcr.io/apalache-mc/apalache:main` image, and CBMC has an official image on Docker Hub with more than 28,000 pulls.

**How much time does it take to find a real bug with TLA+?**
For a focused concurrency question, the first useful specification is often an afternoon: write a small PlusCal or TLA+ model with two or three processes, state the invariant you believe holds, and let TLC try to falsify it. The hard part is usually not the language — it is deciding which slice of the system to model.

**Which tool should a small backend team adopt first in 2026?**
Start with TLA+ and TLC. It is MIT licensed, has the largest community of the three at 3,116 stars, saw upstream commits on 13 October 2026, and it targets the bugs that integration tests miss. Add Apalache when your specifications grow parameters, and reach for CBMC only when you need source-level guarantees in C or C++.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
