---
title: "CaDiCaL vs Kissat vs CryptoMiniSat in 2026: Which SAT Solver Should You Actually Deploy?"
date: "2026-09-25"
tags: ["sat-solver", "formal-verification", "developer-libraries", "combinatorial-optimization"]
draft: false
---

Every time a build system resolves a dependency graph, a hardware team verifies a chip, or a config tool checks whether two firewall rules can ever conflict, something is answering the same question: **is there an assignment of true/false to these variables that satisfies all these constraints?** That question is the Boolean satisfiability problem, it is NP-complete in the worst case, and the reason it is usable in practice is that a handful of carefully engineered CDCL solvers can crack industrial instances with hundreds of thousands of variables.

Those solvers are also surprisingly easy to self-host. All three of the serious open-source options are single-binary C or C++ projects with no cluster, no licence server, and no vendor — **CaDiCaL, Kissat, and CryptoMiniSat**, which between them account for three of the most-cited implementations in the field. Two of them share an author, one automatically compiles the others as part of its own build, and picking wrong costs you either throughput or a feature you did not know you needed.

## TL;DR — the 30-second verdict

- **General-purpose C/C++ work, clean code, active development** → **CaDiCaL**. It is the reference implementation for modern inprocessing-based CDCL, actively pushed (2026-09-24), with a documented C++ API and library build.
- **Maximum raw solving performance on hard combinatorial instances, minimal dependencies** → **Kissat**. Same author, rewritten in plain C, tuned for speed and stability rather than hackability.
- **XOR-heavy problems or incremental solving from Python** → **CryptoMiniSat**. Native XOR clause support, an incremental assumption API, a first-class Python module, and it bundles CaDiCaL as part of its own build.

One-line rule: **start with CaDiCaL, benchmark Kissat before you commit to production, and reach for CryptoMiniSat the moment your problem has XOR constraints or you need incremental calls.**

## Comparison at a glance (data pulled live on 2026-09-25)

| | **CaDiCaL** | **Kissat** | **CryptoMiniSat** |
|---|---|---|---|
| Repository | `arminbiere/cadical` | `arminbiere/kissat` | `msoos/cryptominisat` |
| Language | C++ | C | C++ |
| GitHub stars | 610 | 668 | 938 |
| Licence | MIT | MIT | Open source (README badge shows MIT) |
| Last push | 2026-09-24 | 2025-10-16 | 2026-09-24 |
| Build system | `./configure && make` | `./configure && make test` | CMake + Ninja |
| Dependencies | None beyond a C++ toolchain | None beyond a C toolchain | GMP, zlib, plus auto-fetched CaDiCaL/CadiBack |
| Interfaces | CLI, C++ library (`libcadical.a`) | CLI (binaries per release) | CLI, C++ library, Python |
| Proof output | Yes — `cadical dimacs proof` | Release binaries + source | Yes |
| XOR clauses | No (DIMACS CNF) | No (DIMACS CNF) | Yes — DIMACS extended with XOR |
| Incremental solving | Yes (assumption-based API) | Not its focus | Yes, and exposed in Python |
| Design priority | Understandable, modifiable, fast | Bare-metal speed and simplicity | Features: XOR + incremental |
| Best for | Library embedding, research, default choice | Raw performance on benchmark suites | Cryptographic and XOR-structured instances |

## Decision matrix: pick your use case

| Use case | Recommended | Why |
|---|---|---|
| Embedding a solver inside a C++ verification tool | CaDiCaL | `libcadical.a` plus a documented header with an API example |
| Batch-solving thousands of CNF files in CI | Kissat | Fastest to build, minimal dependencies, statically linkable |
| Cryptanalysis or parity/XOR-heavy constraints | CryptoMiniSat | XOR clauses are first-class, not encoded by hand |
| Incremental solving driven from Python | CryptoMiniSat (`pycryptosat`) | Assumption-based API available directly from a Python object |
| Teaching or extending a CDCL solver | CaDiCaL | Written to be read and modified; CaDiCaL 2.0 paper documents the architecture |
| Getting a verifiable answer for a release gate | Any of the three plus an independent proof checker | Emit a proof trace and check it separately |
| One-off "is this satisfiable?" script | Kissat | Clone, `./configure && make test`, run |

## CaDiCaL — the modern reference CDCL solver

CaDiCaL's stated goal is unusual for high-performance software: be **easy to understand and change** while remaining close to the state of the art. The README is candid that the simplification goal was only partly achieved compared with its predecessor Lingeling, but that the code is much better documented and ended up generally faster, with the notable exception of some parity and cardinality preprocessing.

The build is deliberately boring:

```bash
git clone https://github.com/arminbiere/cadical
cd cadical
./configure && make          # builds ./build/cadical and libcadical.a
./build/cadical -h           # full option list
```

Usage follows the classic DIMACS convention, with an optional second argument for a proof trace:

```bash
# Solve input.cnf, print the result
./build/cadical input.cnf

# Solve and write a proof file you can check independently
./build/cadical input.cnf proof.drat
```

For embedding, the library target is `libcadical.a` and the public header is `src/cadical.hpp`, which ships with a usage example. That combination — a static library, a documented header, and a solver whose internals a normal engineer can follow — is why CaDiCaL shows up inside other projects. **CryptoMiniSat literally fetches and compiles CaDiCaL as part of its own build**, which is about the strongest endorsement one C++ project can give another.

The project publishes a proper academic reference (the CaDiCaL 2.0 tool paper, CAV 2024, LNCS volume 14681), maintains a `NEWS.md` changelog since release 1.5.1, and is pushed almost daily. If you want one default for "SAT solving in C++", this is it.

## Kissat — same author, bare metal, built for speed

Kissat is a deliberate strategy change. The README calls it a **"keep it simple and clean bare metal SAT solver"** written in C, and describes it as a port of CaDiCaL back to C with improved data structures, better scheduling of inprocessing, and optimized algorithms and implementation. In other words: less extensible, more focused, faster.

```bash
git clone https://github.com/arminbiere/kissat
cd kissat
./configure && make test     # configures, builds, and runs the test suite
./build/kissat input.cnf
```

Two practical consequences of the "bare metal" design:

- **The build has effectively no external dependencies**, so it drops cleanly into containers, CI images, and appliances where you do not want GMP or CMake in the dependency tree.
- **Binaries are attached to every major release**, which means you can vendor a tested solver version instead of compiling it on each machine — useful when your build environment is air-gapped.

The trade-off is visible in the repository activity: last push was 2025-10-16, roughly a year before this article, versus daily commits on CaDiCaL. That is not abandonment — it is a stable, finished-feeling solver that gets released rather than churned. If your compatibility policy forbids tracking a fast-moving dependency, Kissat is the calmer choice.

The solver lineage is documented in a SAT Competition 2024 solver description, which is the standard way performance claims are published in this field.

## CryptoMiniSat — XOR clauses and incremental solving from Python

CryptoMiniSat takes a different route: it is an **advanced incremental solver** that accepts standard DIMACS CNF *extended with XOR clauses*, and exposes three interfaces — command line, C++ library, and Python.

Because it is a CMake project with real dependencies, the build is a few more lines:

```bash
# Debian/Ubuntu
sudo apt-get install build-essential cmake ninja-build git libgmp-dev zlib1g-dev

git clone https://github.com/msoos/cryptominisat
cd cryptominisat
mkdir build && cd build
cmake -G Ninja -DCMAKE_BUILD_TYPE=Release ..
cmake --build .
```

Clone-and-build is the cleaner option than hand-installing libraries, because the CMake configuration **automatically fetches and compiles CaDiCaL and CadiBack**, so the only dependency you have to manage is GMP (and zlib).

This is what a DIMACS instance and its result look like — three variables, three clauses:

```plain
p cnf 3 3
1 0
-2 0
-1 2 3 0
```

```bash
cryptominisat5 --verb 0 file.cnf
# s SATISFIABLE
# v 1 -2 3 0
```

Add a fourth clause pinning `-3` and the same instance becomes `s UNSATISFIABLE` — the whole format is just "variables, signed numbers, terminated with 0".

The Python module is the feature that separates CryptoMiniSat for application work. In incremental mode you keep one solver object alive, add clauses as you learn them, and query with temporary assumptions:

```python
from pycryptosat import Solver

s = Solver()
s.add_clause([1])
s.add_clause([-2])
s.add_clause([-1, 2, 3])

sat, solution = s.solve()      # (True, (None, True, False, True))
sat, solution = s.solve([-3])  # assume variable 3 is False -> UNSAT
sat, solution = s.solve()      # assumptions are temporary: still SAT

s.add_clause([-3])             # now it is permanent
sat, solution = s.solve()      # False
```

That distinction between **temporary assumptions** and **permanent clauses** is exactly what you need for counterexample search, bounded model checking, and configuration-space exploration, because it lets you reuse all the learned clauses between queries instead of rebuilding the solver from scratch.

## Pitfalls that cost people weeks

**Encoding is your problem, and it dominates runtime.** None of these solvers will rescue a bad encoding. A direct encoding of a cardinality constraint ("at most 3 of these 500") can produce thousands of clauses where a cardinality-aware encoding produces dozens. CaDiCaL's README openly notes it lacks some parity and cardinality preprocessing found elsewhere, which is a hint: if your instances are stuffed with such constraints, encode them better or benchmark CryptoMiniSat's XOR support instead of blaming the solver.

**"SATISFIABLE" is not "correct".** A solver returning a model tells you a satisfying assignment exists *according to the CNF you handed it*. If your translation from the real problem to CNF was wrong, the answer is confidently useless. For anything gating a release, emit a proof (CaDiCaL supports a proof argument) and check it with an independent checker, or at minimum verify the returned model against the original constraints with your own code.

**Watch the variable numbering convention.** DIMACS variables are 1-indexed, literals are signed, and every clause ends with a `0`. Solvers differ in how they report the model — the CryptoMiniSat Python binding returns a tuple whose first element is `None` because there is no variable 0, which trips up code that assumes index parity with a 0-indexed array.

**Mitigate hard instances with assumptions and timeouts, not hope.** Industrial instances can run for hours. Use a time budget plus the incremental API (assume a phase, solve, learn, repeat) rather than launching one monolithic run, and log the residual instance when you give up so the failing case is reproducible.

**Thread your own parallel portfolio.** These are single-process solvers. If you need to saturate a 64-core machine, run several binaries with different random seeds and option presets and take the first answer — and remember that only one of them needs to finish for a SAT answer, while UNSAT requires every one of them to agree.

If your problems are optimization problems rather than pure satisfiability, our [constraint programming solver comparison](../2026-06-22-constraint-programming-solvers-ortools-gecode-choco-minizinc-chuffed/) covers the CP-SAT and MiniZinc toolchain, and the [compiler explorer guide](../2026-06-18-self-hosted-compiler-explorer-godbolt-code-analysis/) is a good starting point if you want to see what compilers emit for code you are trying to verify. For the hashing primitives that often accompany this kind of work, see the [hash function library comparison](../2026-06-19-hash-function-libraries-xxhash-blake3-murmurhash-cityhash-farmhash/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "CaDiCaL vs Kissat vs CryptoMiniSat in 2026: Which SAT Solver Should You Actually Deploy?",
  "description": "Hands-on 2026 comparison of the CaDiCaL, Kissat and CryptoMiniSat CDCL solvers: build commands, library and Python interfaces, XOR clause support, incremental solving and production pitfalls.",
  "datePublished": "2026-09-25",
  "dateModified": "2026-09-25",
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

**What is a SAT solver actually used for?**
Answering constraint-satisfaction questions at scale: dependency and package resolution, hardware and protocol verification, configuration and feature-model analysis, test-case generation, scheduling feasibility, and cryptanalysis. If your problem can be expressed as "these Boolean constraints must all hold", a CDCL solver can attack it directly.

**Which of the three should I pick first?**
CaDiCaL. It is actively maintained, has a documented C++ API and a library build, and it is the solver other projects embed. Benchmark Kissat against it on your own instances before standardising, because "faster" here is instance-dependent.

**When is CryptoMiniSat worth the extra dependencies?**
Two situations: when your problem naturally contains XOR (parity) constraints, and when you need incremental solving with temporary assumptions — especially from Python, where `pycryptosat` gives you a persistent solver object instead of a process per query.

**Do I need a GPU or a big server to run these?**
No. All three are single-threaded command-line programs that run comfortably on a laptop. Throughput comes from running many solver processes in parallel over a batch of instances, not from a single powerful machine.

**Can I use these from Python without compiling anything?**
For CryptoMiniSat, yes — the incremental Python module is published on PyPI. For the other two, the common pattern is to shell out to the binary and parse the result, or call them via a SAT-solver wrapper library.

**Why is Kissat's repository less active than CaDiCaL's?**
Different development philosophy rather than neglect. Kissat is written for speed and ships binaries with major releases; CaDiCaL is written to be extended and receives near-daily commits. If you need a pinned, rarely-changing dependency, Kissat's slower cadence is a feature.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
