---
title: "C++ Automatic Differentiation in 2026: CppAD vs Adept vs Stan Math vs Sacado"
date: "2026-10-12"
tags: ["cpp", "scientific-computing", "numerical-computing", "developer-tools", "optimization"]
draft: false
cover: "/img/screenshots/cppad-coinor-logo.jpg"
---

Hand-writing analytic derivatives is where good numerical code goes to die. A single sign error in a Jacobian produces a solver that "almost" converges, and a central finite-difference approximation costs you 2n extra function evaluations per gradient — which is brutal when one evaluation is a 30-second simulation.

Algorithmic differentiation (AD, also called automatic differentiation) removes that entire class of bugs. You write the math once, as ordinary C++, and the library propagates exact derivatives through your code using the chain rule. No symbolic algebra, no truncation error, no 2n cost blow-up.

The catch: C++ has four mature AD libraries with genuinely different designs, and picking the wrong one can cost you 10x in runtime or three weeks in build-system pain.

![COIN-OR project logo — the home of CppAD](/img/screenshots/cppad-coinor-logo.jpg "CppAD is maintained by the COIN-OR foundation")

## TL;DR — Quick Verdict

**Choose CppAD if** you need both forward and reverse mode, sparse Jacobians/Hessians for large problems, and you want a library with a documented `ADFun` tape you can reuse across many evaluations. **Choose Stan Math if** you are doing statistical/probabilistic modeling and want the most actively developed reverse-mode library with multithreaded gradient evaluation out of the box. **Choose Adept if** your hot loop is dense scalar/matrix math and you want expression templates that fuse operations plus a bundled Levenberg-Marquardt optimizer. **Choose Sacado if** you already build against Trilinos or you need a drop-in `Fad` scalar type that can be pushed through tens of thousands of lines of existing templated code.

For most new C++ projects in 2026 that are not statistical models: **CppAD for sparse, Stan Math for dense reverse-mode, Sacado for template-heavy legacy codebases.**

## Quick Comparison Table (October 2026)

| Library | GitHub stars | Mode(s) | License | Build system | Depends on | Last push |
|---|---|---|---|---|---|---|
| **CppAD** | 593 | Forward + reverse | EPL-2.0 OR GPL-2.0-or-later | CMake | C++17 compiler, optional Eigen | 2026-10-07 |
| **Adept 2** | 189 | Reverse (expression-template) | Apache-2.0 (library dirs) | Autotools | Optional BLAS/OpenBLAS | 2025-10-05 |
| **Stan Math** | 841 | Reverse (+ forward/mixed) | BSD-3-Clause (TBB is Apache-2.0) | GNU Make / CMake | Intel TBB, Eigen, Boost | 2026-10-11 |
| **Sacado** (Trilinos) | 1,437 (Trilinos) | Forward + reverse | BSD-3-Clause | CMake (Trilinos) | Trilinos + Kokkos | 2026-10-11 |

Two things jump out of that table. First, the star counts are small compared to web tooling — AD is a specialist niche, and 600 stars here means "the standard library for a whole field." Second, Sacado's real footprint is inside Trilinos, so its "repository activity" number is the Trilinos superproject, not a dedicated repo.

## Decision Matrix: Pick in 10 Seconds

| Your situation | Pick | Why |
|---|---|---|
| Large sparse Jacobian/Hessian, reuse tape across iterations | **CppAD** | Sparse differentiation modes and `ADFun` tape reuse are first-class |
| Probabilistic model, need threaded gradients | **Stan Math** | Reverse-mode + TBB threading, actively developed |
| Dense scalar math in a hot loop, want an optimizer included | **Adept** | Expression templates fuse math; LM/CG/L-BFGS bundled |
| Template-heavy codebase already using Trilinos | **Sacado** | `Fad<double>` drops into existing templates |
| You need derivatives of an ODE/linear solver | **CppAD or Sacado** | Explicit support for differentiating through solvers |
| You need a single-header, zero-dependency experiment | **None — write a dual-number type** | All four are real libraries with real build steps |

## CppAD: The Workhorse for Sparse Problems

CppAD (593 stars, pushed October 2026) records your computation onto a tape, then plays that tape back in forward and reverse sweeps. The API is deliberately explicit: you mark independent variables, record a function, and then ask for `Forward`, `Reverse`, `Jacobian`, `SparseJacobian`, or `Hessian` values.

```cpp
#include <cppad/cppad.hpp>
#include <vector>

int main() {
    using CppAD::AD;
    std::vector<AD<double>> x(2), y(1);
    x[0] = 1.0; x[1] = 2.0;

    CppAD::Independent(x);              // start recording
    y[0] = x[0] * x[0] * x[1] + sin(x[0]);
    CppAD::ADFun<double> f(x, y);       // tape is now reusable

    std::vector<double> xp{1.0, 2.0};
    std::vector<double> jac = f.Jacobian(xp);   // [4.54, 1.0]
    std::vector<double> hess = f.Hessian(xp, 0);
    return 0;
}
```

Install it from distro packages or conda, or build from source with CMake:

```bash
# Debian/Ubuntu
sudo apt-get install coinor-libcppad-dev

# conda-forge (gets you a matching modern C++ toolchain too)
conda install -c conda-forge cppad

# from source
git clone https://github.com/coin-or/CppAD.git && cd CppAD
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release -Dcppad_cxx_flags="-std=c++17" ..
make -j"$(nproc)" && sudo make install
```

The tape is CppAD's superpower and its main footgun: **build it once outside your iteration loop**, not inside. A tape rebuilt every iteration turns a 5 ms gradient into a 200 ms gradient.

If you also work with derivative-heavy ODE pipelines, our [comparison of numerical ODE solver libraries](../2026-10-11-numerical-ode-solver-libraries-sundials-odeint-gsl-differentialequations/) covers the integration side of the same workflow.

## Adept 2: Expression Templates and a Bundled Optimizer

Adept (189 stars) stands for "Automatic Differentiation using Expression Templates." Its selling point is that array and scalar expressions are fused at compile time, so `y = a * b + c` does not allocate a chain of temporaries. Adept 2 ships three things in one package: reverse-mode AD, N-dimensional arrays with linear algebra, and minimizers (Levenberg, Levenberg-Marquardt, conjugate gradient, L-BFGS, with optional box constraints).

```cpp
#include <adept_arrays.h>
#include <iostream>

int main() {
    adept::Stack stack;        // holds the tape
    adept::aReal x = 2.0;      // an "active" scalar

    stack.new_recording();     // start recording
    adept::aReal y = 3.0 * x * x + 1.0;

    y.set_gradient(1.0);       // seed the output
    stack.reverse();           // one reverse sweep
    std::cout << "dy/dx = " << x.get_gradient() << "\n";  // 12
    return 0;
}
```

Build from a GitHub snapshot with the standard Autotools flow, and link an optimized BLAS if you plan to do serious matrix work:

```bash
git clone https://github.com/rjhogan/Adept-2.git
cd Adept-2
autoreconf -i
./configure --with-blas="-lopenblas"
make -j"$(nproc)" && make check && sudo make install
```

Adept is the right answer when your derivative cost is dominated by dense linear algebra rather than by tape traffic. Be aware that the release cadence is slow (last push October 2025) — pin a version and vendor it.

## Stan Math: The Most Actively Developed Reverse-Mode Library

Stan Math (841 stars, pushed within the last day at the time of writing) is the C++ engine behind the Stan probabilistic programming language, but it is a standalone header library you can use directly. It is reverse-mode first, built on Eigen, and it parallelizes the reverse sweep with Intel TBB — which matters when you have a 10,000-parameter model and 32 cores.

```cpp
#include <stan/math.hpp>
#include <iostream>

int main() {
    using stan::math::var;
    var x = 2.0;
    var y = x * x + sin(x);

    y.grad();                       // run the reverse sweep
    std::cout << "dy/dx = " << x.adj() << "\n";  // 4 + cos(2) = 3.584
    stan::math::recover_memory();   // release the tape
    return 0;
}
```

Clone it recursively (TBB, Eigen, Boost, Sundials come as submodules) and run the bundled tests:

```bash
git clone --recursive https://github.com/stan-dev/math.git
cd math
make -j"$(nproc)" test/unit/math/prim/prob/std_normal_test
```

Two practical notes. First, `--recursive` is mandatory — a plain clone produces header errors that look like a broken compiler. Second, the memory arena means you should call `recover_memory()` between independent fits, or long-running processes grow without bound.

If your gradients feed a mathematical program, the solver side is covered in our [linear programming solver roundup](../2026-06-26-linear-programming-solvers-glpk-highs-soplex-clp/).

## Sacado: Forward and Reverse Modes as Ordinary Scalar Types

Sacado lives inside Trilinos (1,437 stars for the superproject, active October 2026). Its design is the most "C++-native" of the four: derivatives are carried in scalar types like `Sacado::Fad::DFad<double>`, so a `FadType` can be substituted anywhere a `double` was, including inside deeply nested templates.

```cpp
#include <Sacado.hpp>
#include <iostream>

int main() {
    using FadType = Sacado::Fad::DFad<double>;

    FadType x = 2.0;
    x.diff(0, 1);                  // seed d/dx
    FadType y = 3.0 * x * x + 1.0; // propagates dydx = 6x

    std::cout << "y = " << y.val() << ", dy/dx = " << y.dx(0) << "\n";
    return 0;
}
```

Build it as part of a trimmed Trilinos configuration rather than the whole project:

```bash
git clone https://github.com/trilinos/Trilinos.git
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release \
      -DTrilinos_ENABLE_Sacado=ON \
      -DTrilinos_ENABLE_ALL_PACKAGES=OFF \
      -DTrilinos_ENABLE_Kokkos=ON ..
make -j"$(nproc)" && sudo make install
```

`-DTrilinos_ENABLE_ALL_PACKAGES=OFF` is not optional in practice. A default Trilinos build compiles for hours; the Sacado-only configuration above finishes in minutes and produces exactly the headers you need.

## Build Integration: A Real CMake Setup

All four libraries play nicely with CMake, but each needs different find/link treatment. A minimal `CMakeLists.txt` that handles CppAD and Stan Math looks like this:

```cmake
cmake_minimum_required(VERSION 3.20)
project(gradient_demo CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(CppAD CONFIG REQUIRED)

find_path(STAN_MATH_INC "stan/math.hpp"
  HINTS /opt/stan-math /usr/local/include)
find_library(TBB_LIB tbb)

add_executable(demo main.cpp)
target_link_libraries(demo PRIVATE CppAD::cppad)
target_include_directories(demo PRIVATE ${STAN_MATH_INC})
target_link_libraries(demo PRIVATE ${TBB_LIB})
```

For CI, cache the library install (`~/.cache/cppad`) and use `-DCMAKE_BUILD_TYPE=Release` everywhere — every one of these libraries is header-heavy, and a debug build of a template-instantiation-heavy translation unit can be 20x slower to compile and run.

## Pitfalls, Migration Notes, and Performance Traps

**1. Rebuilding the tape inside a loop.** The single most common performance bug in every one of these libraries. Record once, evaluate many times.

**2. Forgetting to clear the tape.** Stan Math's arena and Adept's `Stack` both accumulate recordings. A long-lived service that never calls `recover_memory()` or `new_recording()` will leak until it dies.

**3. Mixing `double` and active types silently.** `FadType y = 3.0 * x * x;` works, but `double z = 3.0 * x * x;` compiles in some configurations and silently drops the derivative information you were about to use. Turn on `-Wall -Wconversion` and review every narrowing assignment.

**4. Assuming reverse mode is always faster.** Reverse mode costs roughly one sweep regardless of parameter count, but it carries a tape of the whole computation. For a function with 3 inputs and 1 output that you call a million times, forward mode with a dual number is dramatically cheaper.

**5. Ignoring sparsity.** CppAD's `SparseJacobian` and `SparseHessian` exploit structural zeros. Reaching for the dense `Jacobian()` on a 5,000-variable problem is the difference between milliseconds and minutes.

**6. Thread-safety assumptions.** Stan Math's TBB-parallel reverse sweep requires that you do not share mutable tape state across threads. Adept's `Stack` is per-thread by design; sharing one across a thread pool produces nondeterministic gradients.

**7. Digit-level debugging.** When gradients disagree with finite differences, check the step size before blaming the AD library — central differences with `h = 1e-8` on a function whose values are ~1e6 has essentially no valid digits left.

## Which Should You Actually Install?

If you are writing new numerical C++ in 2026 and you do not have a Trilinos dependency, **start with CppAD**: it is the most explicit about what it is doing, supports both modes, handles sparsity, and installs from apt or conda in one command. Reach for **Stan Math** the moment your problem looks like a statistical model with thousands of parameters, because TBB-parallel reverse sweeps are not something you want to retrofit. Choose **Adept** when dense array math dominates and you would rather not write your own Levenberg-Marquardt loop. Choose **Sacado** when the codebase already lives in Trilinos or Kokkos land — as a bonus, the same mathematical foundation covers template linear algebra, which we compared in depth in our [C++ template linear algebra roundup](../2026-06-27-cpp-template-linear-algebra-libraries-armadillo-blaze-xtensor/).

Whichever you pick, the workflow that keeps gradients honest is the same: build a small test function with a hand-derivable derivative, assert your AD result against it to 1e-10, and only then move on to the real model. Numerical code without that test is guesswork with extra steps.

## FAQ

### Which C++ automatic differentiation library should I use in 2026?

For general-purpose work needing both forward and reverse mode with sparse support, **CppAD**. For statistical models needing fast threaded reverse-mode gradients, **Stan Math**. For dense array math with a bundled optimizer, **Adept 2**. For codebases already in the Trilinos/Kokkos ecosystem, **Sacado**.

### Is algorithmic differentiation the same as finite differences?

No. Finite differences approximate derivatives by evaluating the function at perturbed points, which costs 2n extra evaluations for a full gradient and introduces truncation and cancellation error. Algorithmic differentiation applies the chain rule exactly to the recorded computation, so the derivative is accurate to machine precision and costs a small multiple of one function evaluation.

### Forward mode or reverse mode — which do I need?

It depends on the shape of your function: f: R^n → R^m. Forward mode costs roughly proportional to n, so it wins when you have few inputs. Reverse mode costs roughly proportional to m, so it wins when you have few outputs and many parameters — which is why every optimization and statistical modeling library is reverse-mode first. CppAD and Sacado support both; Stan Math is reverse-mode centric.

### Can these libraries differentiate through linear solvers, ODE integration, and iterative algorithms?

Yes, but the cost depends on the approach. The naive path records the entire iterative solve onto the tape, which is memory-hungry. The better path implements the adjoint/checkpointing method for the solver — most solver libraries, including the ODE integrators in Stan Math, expose that interface. If you differentiate through an ODE, pair the AD library with a solver that supports adjoint sensitivity analysis.

### Do I need a GPU or special hardware?

No. All four libraries are CPU libraries and will run on any x86-64 or ARM machine. Stan Math can use Intel TBB to parallelize the reverse sweep across cores, and Sacado can build on Kokkos for accelerator backends, but neither is required to get started.

### How do I verify that my gradients are correct?

Write a unit test with a function whose derivative you can compute by hand, and compare against the library result with a tolerance around 1e-10 (double precision, well-conditioned problem). Then repeat with a randomized input. If you must cross-check with finite differences, use central differences with a step size derived from the function magnitude (roughly `1e-5 * max(1, |f(x)|)`), not a fixed `1e-8`.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "C++ Automatic Differentiation in 2026: CppAD vs Adept vs Stan Math vs Sacado",
  "description": "A practical 2026 comparison of C++ algorithmic differentiation libraries — CppAD, Adept 2, Stan Math and Sacado — with install commands, CMake integration, code examples and performance pitfalls.",
  "datePublished": "2026-10-12",
  "dateModified": "2026-10-12",
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
