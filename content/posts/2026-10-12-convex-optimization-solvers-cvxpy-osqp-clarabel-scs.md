---
title: "Convex Optimization Solvers in 2026: CVXPY vs OSQP vs Clarabel vs SCS"
date: "2026-10-12"
tags: ["optimization", "scientific-computing", "numerical-computing", "python", "developer-tools"]
draft: false
cover: "/img/screenshots/osqp-benchmark-profiles.jpg"
---

The slowest line in your scheduling engine, your portfolio rebalancer, or your model-predictive controller is almost never your own code. It is the solver call — and the difference between a badly matched solver and a well matched one is routinely **10x to 50x in wall-clock time**, not 10%.

Convex optimization in 2026 has a clean separation of concerns that most tutorials blur together: **CVXPY is a modeling language, not a solver**, and OSQP, Clarabel and SCS are the solvers it calls underneath. Understanding which layer does what is the single biggest lever you have over performance.

![OSQP official performance profiles comparing open-source quadratic programming solvers](/img/screenshots/osqp-benchmark-profiles.jpg "Official OSQP benchmark: performance profiles across open-source QP solvers")

## TL;DR — Quick Verdict

**Use CVXPY if** you want to describe the problem once in readable math and let the library pick the solver and handle mixed-integer or non-convex-adjacent modeling classes. **Use OSQP directly if** you solve the same-shaped quadratic program thousands of times per second and need warm starting, updatable matrices, and code generation for embedded targets. **Use Clarabel if** you need second-order cone or semidefinite constraints solved to high accuracy with an interior-point method. **Use SCS if** your problem has exponential or power cones, is semidefinite, or is so large that a first-order method's lower memory footprint matters more than the last three digits of accuracy.

In practice: **model in CVXPY, benchmark with all three solvers CVXPY ships with, then graduate to a direct solver API for the hot path.**

## Quick Comparison Table (October 2026)

| Project | Stars | Role | Problem classes | Language | License | Last push |
|---|---|---|---|---|---|---|
| **CVXPY** | 6,361 | Modeling language | Convex, mixed-integer convex, geometric, quasiconvex, nonlinear | Python (C++ extensions) | Apache-2.0 | 2026-10-11 |
| **OSQP** | 2,208 | Solver (operator splitting) | Quadratic programs | C (Python/C++/Julia wrappers) | Apache-2.0 | 2026-01-12 |
| **Clarabel.rs** | 617 | Solver (interior point) | LP, QP, SOCP, SDP, exponential and power cones | Rust (Python wrapper) | Apache-2.0 | 2026-04-13 |
| **SCS** | 638 | Solver (operator splitting) | LP, SOCP, SDP, exponential and power cones | C | MIT | 2026-10-06 |

CVXPY's dependency list tells the whole story: installing CVXPY pulls in **Clarabel, OSQP, SCS and HiGHS** automatically, because the modeling layer needs a solver per problem shape. You are already running all four projects the moment you `pip install cvxpy`.

## Decision Matrix: Pick in 10 Seconds

| Your situation | Pick | Why |
|---|---|---|
| First version of anything, unknown problem shape | **CVXPY** | Solver-agnostic model, instant prototyping |
| Same QP shape, thousands of solves per second | **OSQP direct** | Warm starting + `update()` on matrices/vectors |
| Second-order cone or semidefinite constraints | **Clarabel** | Interior point, high accuracy on conic problems |
| Exponential/power cones, very large problems | **SCS** | Handles all cone types, low memory per iteration |
| Mixed-integer program | **CVXPY + HiGHS** | OSQP/Clarabel/SCS are continuous-only |
| Embedded C/Rust deployment | **OSQP or Clarabel.rs** | Both have code generation / native Rust builds |
| Non-convex as written | **None of these** | Rewrite or relax; these are convex solvers |

## CVXPY: The Modeling Layer You Should Start With

CVXPY (6,361 stars, pushed October 2026) lets you write the problem as math rather than as a sparse matrix assembly routine. You declare variables, write constraints with ordinary Python comparisons, and call `solve()`.

```bash
pip install cvxpy
# or, for a self-contained scientific stack:
conda install -c conda-forge cvxpy
```

```python
import cvxpy as cp
import numpy as np

np.random.seed(0)
n, m = 50, 120
A = np.random.randn(m, n)
b = np.random.randn(m)
x = cp.Variable(n)

objective = cp.Minimize(cp.sum_squares(A @ x - b) + 0.1 * cp.norm1(x))
constraints = [x >= 0, cp.sum(x) == 1]
problem = cp.Problem(objective, constraints)
problem.solve(solver=cp.CLARABEL)

print(problem.status, problem.value)
print(x.value[:5])
```

Two details matter operationally. First, `problem.solve(solver=cp.OSQP)` lets you force a specific backend — this is how you benchmark without rewriting your model. Second, CVXPY enforces **DCP (disciplined convex programming) rules**, which means it will refuse to compile a problem that is not provably convex. That refusal is a feature: it catches sign errors before they become wrong answers.

![CVXPY wordmark](/img/screenshots/cvxpy-wordmark.png "CVXPY — the Python-embedded modeling language for convex optimization")

If you later discover that the linear algebra dominates instead of the cone work, our [C++ template linear algebra comparison](../2026-06-27-cpp-template-linear-algebra-libraries-armadillo-blaze-xtensor/) covers the dense-matrix side of the pipeline.

## OSQP: Warm Starting and Updatable QPs

OSQP (2,208 stars) solves exactly one problem class and does it extremely well:

```
minimize        0.5 x' P x + q' x
subject to      l <= A x <= u
```

Its operator-splitting (ADMM-style) design means each iteration is cheap, and — crucially — the **workspace can be reused**. When only `q`, `l`, or `u` change between calls, you call `update()` instead of rebuilding and re-factorizing.

```bash
pip install osqp
```

```python
import osqp, numpy as np
from scipy import sparse

P = sparse.csc_matrix([[4, 1], [1, 2]])
q = np.array([1, 1])
A = sparse.csc_matrix([[1, 1], [1, 0], [0, 1]])
l = np.array([1, 0, 0])
u = np.array([1, 0.7, 0.7])

prob = osqp.OSQP()
prob.setup(P, q, A, l, u, alpha=1.0)
prob.update_settings(polishing=1)      # tighter final accuracy
res = prob.solve(raise_error=True)

print(res.info.status, res.info.obj_val, res.x)
```

For a receding-horizon controller or a real-time portfolio loop, the pattern is: `setup()` once, then `prob.update(q=q_new, l=l_new, u=u_new)` and `solve()` per tick. That is the entire reason OSQP is popular in embedded contexts — and the same C core is available through C, C++, Julia and Fortran interfaces.

Install the native library when you are not in Python:

```bash
git clone --recursive https://github.com/osqp/osqp.git
cd osqp && mkdir build && cd build
cmake -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release ..
cmake --build . --target install
```

The `--recursive` flag matters: OSQP vendors QDLDL as a submodule, and a non-recursive clone fails at CMake configure time with a confusing missing-file error.

## Clarabel: Interior Point for Conic Problems

Clarabel.rs (617 stars) is a Rust implementation of an interior-point solver built around a homogeneous embedding, which is what gives it reliable performance on infeasible and unbounded problems. It handles **linear programs, quadratic programs, second-order cone programs, semidefinite programs, and exponential/power cones** in a single API.

Rust projects add it in one line:

```toml
[dependencies]
clarabel = "0"
```

Python users get the same solver:

```bash
pip install clarabel
```

```python
import clarabel
import numpy as np
from scipy import sparse

P = sparse.csc_matrix([[3.0, 1.0], [1.0, 2.0]])
q = np.array([-1.0, -4.0])
A = sparse.csc_matrix([[1.0, 1.0], [1.0, 0.0], [0.0, 1.0]])
b = np.array([1.0, 0.7, 0.7])

cones = [clarabel.NonnegativeConeT(3)]
settings = clarabel.DefaultSettings()
solver = clarabel.DefaultSolver(P, q, A, b, cones, settings)
solution = solver.solve()

print(solution.status, solution.obj_val, solution.x)
```

Pick Clarabel when your constraint set is genuinely conic — a second-order cone from a robustness radius, or a semidefinite constraint from a Lyapunov condition. Interior-point methods converge in tens of iterations regardless of problem conditioning, which is why they hold up on badly scaled models where first-order methods crawl.

## SCS: Splitting Conic Solver for the Hard Cone Types

SCS (638 stars, MIT licensed) is the other first-order option, and it is broader than OSQP: it solves **LP, SOCP, SDP, exponential cone and power cone** problems. CVXPY uses it as the default for semidefinite and exponential-cone problems for exactly that reason.

```bash
pip install scs
```

```python
import scs
import numpy as np
from scipy import sparse

# minimize c'x  s.t.  Ax + s = b,  s in K
A = sparse.csc_matrix([[1.0, 1.0], [1.0, 0.0], [0.0, 1.0]])
b = np.array([1.0, 0.7, 0.7])
c = np.array([-1.0, -4.0])

data = {"A": A, "b": b, "c": c}
cone = {"z": 1, "l": 2}     # 1 equality row, 2 nonnegative rows
sol = scs.solve(data, cone, verbose=False)

print(sol["info"]["status"], sol["info"]["pobj"], sol["x"])
```

The `cone` dictionary is the API's core idea: `z` = zero cone (equalities), `l` = nonnegative, `q` = second-order, `s` = semidefinite, `ep`/`ed` = exponential, `p` = power. Once you internalize that mapping, you can express almost any convex program SCS supports without a modeling layer.

Be realistic about accuracy: SCS is first-order, so expect roughly 1e-5 to 1e-7 relative accuracy by default. For final numbers, either raise `eps_abs`/`eps_rel` and iteration limits, or polish with an interior-point solver.

## Performance and Numerical Pitfalls That Actually Bite

**1. Passing dense matrices.** All three solvers want sparse CSC input. Converting a dense `numpy` array with `sparse.csc_matrix(A)` is not optional for large problems — dense input can multiply memory by 100x and destroy the sparsity-aware factorization.

**2. Rebuilding instead of updating.** The most expensive mistake in a control loop. OSQP's `update()` exists to avoid re-factorization; using `setup()` per tick throws away the entire advantage.

**3. Expecting a first-order method to give you 1e-12.** OSQP and SCS trade final accuracy for per-iteration cost. If you need near-machine-precision answers, enable polishing or hand the final problem to Clarabel.

**4. Ignoring scaling.** Conic solvers are sensitive to row/column scaling of `A` and `P`. If you see statuses like "solved inaccurate" on a well-posed problem, normalize your data ranges first — this fixes more problems than any solver setting.

**5. Version skew between CVXPY and the solvers.** CVXPY declares minimum versions (Clarabel >= 0.5.0, OSQP >= 1.0.0, SCS >= 3.2.4). A pinned older solver in a locked virtual environment produces "solver not installed" errors that look like CVXPY bugs.

**6. Treating CVXPY as a solver.** CVXPY compiles your model into a canonical form, chooses a solver, and translates results back. When it reports `solver_error`, the problem is usually in the canonicalization layer or the solver selection, not in "CVXPY."

**7. Mixed-integer problems in a continuous solver.** OSQP, Clarabel and SCS solve continuous problems only. A mixed-integer program needs HiGHS or another MIP solver; CVXPY will route it there automatically if you install it.

## Tooling Around the Core Solvers

Two operational habits pay for themselves immediately. First, keep a **problem-shape benchmark** in CI: fix the dimensions, run CVXPY with `solver=cp.OSQP`, `cp.CLARABEL` and `cp.SCS`, and record iterations and solve time. When a dependency upgrade changes behavior, you find out in the benchmark rather than in production. Second, log `problem.status` and `solver_stats.solver_name` on every solve — "optimal" and "optimal_inaccurate" are very different answers to ship.

If your convex program sits on top of large sparse factorizations, the solver-level details in our [sparse linear solver roundup](../2026-06-22-sparse-linear-solvers-suitesparse-mumps-petsc-hypre-superlu/) are the natural next read; and if your bottleneck is the dense BLAS underneath, the [numerical computing libraries comparison](../2026-06-21-numerical-computing-libraries-openblas-lapack-eigen/) covers that layer.

## Which Stack Should You Actually Install?

For 90% of teams: **`pip install cvxpy` and model there.** You get Clarabel, OSQP, SCS and HiGHS in one command, you can switch solvers with a keyword argument, and DCP rules catch convexity mistakes early. Move to a direct solver API only when a profiler tells you the modeling layer or the factorization is the bottleneck — and then choose OSQP for repeated QPs, Clarabel for conic accuracy, and SCS for the cone types nobody else accepts.

## FAQ

### Is CVXPY a solver?

No. CVXPY is a modeling language that compiles your problem into a canonical form and calls a numerical solver. It ships with Clarabel, OSQP, SCS and HiGHS by default, and supports additional solvers if you install them separately. When people say "CVXPY was slow," they usually mean "the solver CVXPY picked was wrong for this problem shape."

### Which is faster, OSQP or Clarabel?

It depends on problem shape and how many solves you perform. **OSQP wins on repeated solves of the same structure** because warm starting and `update()` avoid re-factorization, which is why it dominates in embedded and control contexts. **Clarabel wins on one-shot conic problems where you need high accuracy** — an interior-point method typically reaches tighter tolerances in a similar number of iterations. Benchmark with your own data before committing.

### Can these solvers handle semidefinite or exponential cones?

Clarabel and SCS both handle semidefinite, exponential-cone and power-cone problems. OSQP is a quadratic programming solver only (linear constraints), and CVXPY will route an SDP to Clarabel or SCS rather than OSQP. If you write a semidefinite constraint and force `solver=cp.OSQP`, CVXPY will reject it as unsupported.

### Do these solvers support integer or binary variables?

Not directly. CVXPY supports mixed-integer convex problems, but it delegates them to a MIP-capable solver such as HiGHS or another installed backend. OSQP, Clarabel and SCS all solve continuous problems only.

### How accurate is SCS compared to an interior-point solver?

SCS is a first-order splitting method, so default tolerances land around 1e-5 to 1e-7 relative accuracy, and you can tighten them at the cost of more iterations. Interior-point solvers like Clarabel typically reach much tighter tolerances on well-scaled problems. A common production pattern is to solve large instances with SCS and polish the final answer with an interior-point method.

### How do I choose between modeling in CVXPY and calling a solver directly?

Start in CVXPY: it is faster to write, harder to get wrong, and solver-agnostic, so you can swap backends with one argument. Move to a direct API (OSQP, Clarabel, SCS) when profiling shows the modeling/canonicalization overhead or the repeated factorization is the real cost. Keep the CVXPY version as a reference implementation to test the hand-optimized one against.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Convex Optimization Solvers in 2026: CVXPY vs OSQP vs Clarabel vs SCS",
  "description": "A practical 2026 comparison of open-source convex optimization tooling — CVXPY, OSQP, Clarabel and SCS — covering problem classes, install commands, working code examples, warm starting and numerical pitfalls.",
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
