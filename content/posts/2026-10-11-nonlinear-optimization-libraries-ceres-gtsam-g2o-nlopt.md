---
title: "Ceres Solver vs GTSAM vs g2o vs NLopt in 2026: Which Nonlinear Optimization Library Should You Actually Use?"
date: "2026-10-11"
tags: ["optimization", "scientific-computing", "robotics", "cpp", "numerical-computing"]
draft: false
cover: "/img/screenshots/g2o-viewer.jpg"
---

Your bundle adjustment job is 40% of the way through a 3,000-image photogrammetry run, and it has been stuck on the same residual norm for eleven minutes. You picked the wrong solver stack. Nonlinear optimization libraries are not interchangeable: a library built for small dense problems will happily eat 32 GB of RAM on a sparse pose graph, and a graph optimizer tuned for robotics will refuse to accept the generic constraint you need.

This guide compares the four libraries that actually show up in 2026 production systems — **Ceres Solver (4,580★, updated 2026-10-11), GTSAM (3,739★, 2026-10-10), g2o (3,471★, 2026-10-05), and NLopt (2,280★, 2026-06-06)** — with real install commands pulled from their repositories and honest notes on where each one falls apart.

## TL;DR: The 30-Second Verdict

- **General-purpose least squares, robust loss functions, huge sparse problems → Ceres Solver.** It is the default answer for 80% of engineering teams, and the automatic differentiation plus loss-function library is what you are really choosing it for.
- **Robotics, SLAM, sensor fusion, incremental solving → GTSAM.** Factor graphs and iSAM2 are a different data model, not just a different API.
- **Teaching, research codebases, ORB-SLAM-style pipelines → g2o.** Lightweight, easy to read, ships a viewer, and is already the substrate of several well-known SLAM systems.
- **Black-box objectives, no gradients, many free algorithms, small parameter counts → NLopt.** Forty-plus algorithms behind one tiny API, but no sparsity support and no factor-graph machinery.

If you only remember one line: **Ceres for sparse numerical work, GTSAM for probabilistic robotics, g2o for research, NLopt for derivative-free problems.**

## The Contenders at a Glance

| Library | Stars / Last push | Language | License | Derivative handling | Sparse block support | Best-fit workload |
|---|---|---|---|---|---|---|
| **Ceres Solver** | 4,580★ / 2026-10-11 | C++ (Python via bindings) | BSD-3-Clause | Automatic (forward/Jet), analytic, numeric | Yes — Schur, sparse normal Cholesky | Bundle adjustment, calibration, large least squares |
| **GTSAM** | 3,739★ / 2026-10-10 | C++ (Python wrapper) | BSD | Analytic + optional automatic | Yes — factor graph / Bayes tree | SLAM, IMU fusion, incremental inference |
| **g2o** | 3,471★ / 2026-10-05 | C++ | BSD | Analytic (hand-written Jacobians) | Yes — hypergraph | Research SLAM, pose graph teaching |
| **NLopt** | 2,280★ / 2026-06-06 | C, with C++/Fortran/Python/Julia/R bindings | MIT (some bundled algorithms LGPL) | Optional gradient, or derivative-free | No | Black-box optimization, parameter fitting with few variables |

Two numbers worth internalizing: Ceres was pushed **the same day this article was written**, GTSAM the day before. This is not a dead-tool comparison — every one of these projects is actively maintained in 2026.

## Use-Case Decision Matrix

| Your situation | Pick | Why |
|---|---|---|
| 500–50,000 camera poses, sparse Jacobian | **Ceres Solver** | `SPARSE_NORMAL_CHOLESKY` + `DENSE_SCHUR` handle this with one line of solver config |
| Adding IMU preintegration to an existing SLAM stack | **GTSAM** | Preintegrated factors and iSAM2 are already built and tested |
| Need a robust loss for 2% outlier measurements | **Ceres Solver** | `HuberLoss`, `CauchyLoss`, `TukeyLoss` are one argument away |
| Objective is a call to an external simulator (no Jacobian) | **NLopt** | `NLOPT_GN_*` algorithms need zero derivatives |
| Reading/teaching how pose graph optimization works | **g2o** | Smallest codebase; the examples are readable in one sitting |
| Optimizing 12 parameters of a physical model | **NLopt** | Dense-only assumption is irrelevant; BOBYQA and COBYLA just work |
| Need a license-clean permissive dependency for a shipped product | **Ceres, GTSAM, g2o** | All BSD-family; GSL, by contrast, is GPL-3.0 |

## Ceres Solver — The General-Purpose Workhorse

Ceres has been in production at Google since 2010 and the API shows it: the problem/solver split, the `CostFunction` abstraction, and the built-in loss functions are what every other C++ least-squares library gets compared against. It requires Eigen (3.3+), and optionally glog, gflags, and SuiteSparse for the sparse linear solver backends.

**Build from source (official repository):**

```bash
git clone https://github.com/ceres-solver/ceres-solver.git
cd ceres-solver
cmake -S . -B build -DBUILD_TESTING=OFF -DBUILD_EXAMPLES=OFF
cmake --build build -j"$(nproc)"
sudo cmake --install build
```

Distributions also ship packaged builds (`libceres-dev` on Debian/Ubuntu, `ceres-solver` in Homebrew). For a first problem, the canonical example from the Ceres tutorial is two dozen lines:

```cpp
#include <ceres/ceres.h>

struct CostFunctor {
  template <typename T>
  bool operator()(const T* const x, T* residual) const {
    residual[0] = T(10.0) - x[0];
    return true;
  }
};

int main() {
  double x = 5.0;

  ceres::Problem problem;
  ceres::CostFunction* cost =
      new ceres::AutoDiffCostFunction<CostFunctor, 1, 1>(new CostFunctor);
  problem.AddResidualBlock(cost, nullptr, &x);

  ceres::Solver::Options options;
  options.linear_solver_type = ceres::DENSE_QR;
  options.minimizer_progress_to_stdout = true;

  ceres::Solver::Summary summary;
  ceres::Solve(options, &problem, &summary);
  return 0;
}
```

![Least-squares curve fitting example rendered from the Ceres Solver documentation](/img/screenshots/ceres-least-squares-fit.jpg "Ceres Solver least-squares fitting figure from the official documentation")

The automatic differentiation is the feature you are quietly buying. You write the residual as templated C++ and Ceres generates the Jacobian — no analytic derivation, no finite-difference accuracy loss. For residual blocks where you *do* know the closed form, `SizedCostFunction` still lets you hand-write the Jacobian and claw back 2–4x in wall-clock time.

**Choose Ceres when:** your problem is "minimize a sum of squared residuals", the parameter count is in the thousands to millions, and the Jacobian is sparse.

## GTSAM — Factor Graphs for Robotics

GTSAM models the world as a **factor graph**: variables are nodes, measurements are factors, and inference is done on a Bayes tree. That structural difference is the reason GTSAM wins on incremental problems — when a new measurement arrives you update the affected part of the tree instead of re-solving from scratch. `ISAM2` is the workhorse.

**Build from source (instructions taken from the repository's README):**

```bash
sudo apt-get install libboost-all-dev   # optional, several factors require it
sudo apt-get install libtbb-dev         # parallelization, on by default

git clone https://github.com/borglab/gtsam.git
cd gtsam
cmake -S . -B build
cmake --build build --target install
```

The solve loop is deliberately small — the complexity lives in how you build the graph:

```cpp
#include <gtsam/nonlinear/NonlinearFactorGraph.h>
#include <gtsam/nonlinear/LevenbergMarquardtOptimizer.h>

gtsam::NonlinearFactorGraph graph;
// graph.emplace_shared<...>(...) for each measurement

gtsam::Values initialEstimate;
gtsam::LevenbergMarquardtOptimizer optimizer(graph, initialEstimate);
gtsam::Values result = optimizer.optimize();
```

GTSAM is also the heaviest dependency of the four: Boost plus TBB plus a large template-heavy codebase means a full build from source is a coffee break, not a `make -j4` moment. Budget for it, or use a prebuilt package where one exists for your distribution.

## g2o — The Graph Optimizer Inside ORB-SLAM

g2o (General Graph Optimization) is a hypergraph-based optimizer and the optimization backend behind several landmark visual SLAM systems. Its selling point in 2026 is not features but **legibility**: the examples are compact, the classes are small, and the included viewer makes a converged pose graph visible in seconds — which is exactly what you want when debugging a loop closure.

![g2o viewer showing an optimized pose graph](/img/screenshots/g2o-viewer.jpg "The g2o viewer rendering an optimized graph — the fastest way to eyeball a loop closure")

**Install with distribution dependencies (command taken from the project README):**

```bash
sudo apt install libeigen3-dev libspdlog-dev libsuitesparse-dev \
  qtdeclarative5-dev qt5-qmake libqglviewer-dev-qt5

git clone https://github.com/RainerKuemmerle/g2o.git
cd g2o && mkdir build && cd build
cmake ..
make -j"$(nproc)"
```

The trade-off is explicit: g2o expects **analytic Jacobians**. You derive them yourself and encode them in an `Edge` subclass. That is excellent for understanding the math and terrible for shipping fast — which is precisely why Ceres and GTSAM exist.

## NLopt — 40+ Algorithms Behind One API

NLopt is a different animal. It is not a least-squares library; it is a **unified wrapper over dozens of optimizers** — local gradient-based (L-BFGS, MMA, SLSQP, TNewton), local derivative-free (COBYLA, BOBYQA, Nelder-Mead, PRAXIS), and global (DIRECT, CRS, MLSL, ESCH). One interface, many algorithms, and you switch algorithm families by changing a single enum.

```bash
pip install nlopt          # Python bindings
# C/C++: build from source per the official installation instructions
# Julia: using Pkg; Pkg.add("NLopt")
```

```python
import nlopt
import numpy as np

def objective(x, grad):
    if grad.size > 0:
        grad[:] = [2.0 * (x[0] - 3.0), 2.0 * (x[1] + 1.0)]
    return (x[0] - 3.0) ** 2 + (x[1] + 1.0) ** 2

opt = nlopt.opt(nlopt.LD_LBFGS, 2)
opt.set_min_objective(objective)
opt.set_lower_bounds([-10.0, -10.0])
opt.set_upper_bounds([10.0, 10.0])
opt.set_xtol_rel(1e-8)
x_opt = opt.optimize([0.0, 0.0])
```

**The catch:** NLopt is dense-only and has no notion of sparsity, blocks, or factor graphs. Feed it a 10,000-variable bundle adjustment and you will watch memory climb linearly while the solver does dense linear algebra. It is the right tool for a 12-parameter physical model, a hyperparameter search, or an objective that only exists as a compiled simulator.

## Performance, Build Cost, and Licensing Reality Check

Three practical axes that decide more projects than benchmarks do:

1. **Build weight.** Ceres builds in minutes on a normal machine. GTSAM is heavy (Boost + TBB + deep templates). g2o is light but drags Qt in when you enable the viewer. NLopt compiles in seconds.
2. **Convergence behavior.** All four converge on well-conditioned problems. The difference appears with outliers: Ceres' loss functions and GTSAM's robust noise models down-weight garbage measurements; NLopt's algorithms assume your objective is honest, so a single bad simulator call can derail the whole run.
3. **Licensing.** Ceres is BSD-3-Clause, GTSAM and g2o are BSD, and NLopt is MIT with a few bundled algorithms under LGPL. If you are shipping a proprietary product this matters: **GNU GSL, the other common numerical dependency, is GPL-3.0**, which is why teams that cannot take a copyleft dependency migrate to Ceres or GTSAM even when GSL would technically do the job.

## Pitfalls and Migration Traps

- **Analytic Jacobians silently going stale.** g2o and hand-written Ceres cost functions regenerate nothing automatically. Change the residual formula, forget the Jacobian, and you get slow convergence rather than a wrong answer — the worst failure mode, because it looks like a tuning problem.
- **Dense solver choices on sparse problems.** Setting `DENSE_QR` in Ceres on a problem with thousands of poses is the single most common performance mistake. Use `SPARSE_NORMAL_CHOLESKY` or Schur-complement based options.
- **Assuming GTSAM's Python wrapper is feature-complete.** The C++ API moves faster; check that the factor or noise model you need is exposed before committing to a Python-only architecture.
- **Assuming NLopt will scale.** It will not. Move to Ceres/GTSAM the moment parameter count crosses a few hundred.
- **Forgetting that these are libraries, not services.** If you want a hosted optimizer endpoint, you are building it yourself — wrap the C++ binary in a small queue worker and expose it over your own API.

## Why This Matters for Self-Hosted Mapping and Simulation Stacks

Every photogrammetry pipeline, robot fleet, and sensor-fusion deployment built on your own hardware eventually needs a solver it can run locally — no cloud credits, no per-request pricing, no data leaving the machine. That is the same argument that pushed teams toward self-hosted scientific tooling elsewhere: run the mesh, PDE, and geometry stages on hardware you control.

- For the finite-element side of the pipeline, see our [finite element analysis comparison](../2026-06-13-self-hosted-finite-element-analysis-dealii-fenics-mfem-libmesh/).
- When the linear algebra inside your solver becomes the bottleneck, the [sparse linear solver comparison](../2026-06-22-sparse-linear-solvers-suitesparse-mumps-petsc-hypre-superlu/) covers the backends Ceres and GTSAM delegate to.
- For spatial indexing and geometry queries that feed these optimizers, our [computational geometry libraries guide](../2026-06-20-spatial-index-computational-geometry-libraries-libspatialindex-geos-s2-boost-rbush/) walks through the alternatives.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Ceres Solver vs GTSAM vs g2o vs NLopt in 2026: Which Nonlinear Optimization Library Should You Actually Use?",
  "description": "A practical 2026 comparison of Ceres Solver, GTSAM, g2o and NLopt: install commands, code examples, sparse block support, licensing and real use-case decision guidance.",
  "datePublished": "2026-10-11",
  "dateModified": "2026-10-11",
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

**Which nonlinear optimization library should I start with in 2026?**
Start with **Ceres Solver**. It has the widest workload coverage, the best documentation, automatic differentiation that removes an entire class of bugs, and a direct upgrade path to sparse solvers when your problem grows. Only switch when you have a specific reason: incremental inference (GTSAM), teaching/research readability (g2o), or derivative-free black-box objectives (NLopt).

**Is GTSAM better than Ceres for SLAM?**
For **incremental** SLAM — where measurements arrive continuously and you want to update without re-solving everything — yes, GTSAM's Bayes tree and iSAM2 are structurally better suited. For batch bundle adjustment on a fixed dataset, Ceres is typically easier to set up and just as accurate. The data model, not raw speed, is usually the deciding factor.

**Does NLopt support sparse problems or large parameter counts?**
No. NLopt is a dense optimizer collection. It is excellent below a few hundred variables and unsuitable above. If you are optimizing camera poses or a large sensor network, use Ceres Solver or GTSAM instead — NLopt will consume memory linearly and slow to a crawl.

**Which of these libraries are safe for a commercial closed-source product?**
Ceres Solver (BSD-3-Clause), GTSAM (BSD) and g2o (BSD) are all permissive and safe to link into proprietary software. NLopt is MIT with a few algorithms under LGPL, which requires care if you statically link those specific components. By contrast, **GNU GSL is GPL-3.0**, so it is not usable in the same way without copyleft obligations.

**Do I need to hand-write Jacobians?**
No for Ceres (automatic differentiation via `AutoDiffCostFunction`) and not usually for GTSAM. Yes for g2o, which is analytic-Jacobian by design. NLopt takes gradients optionally, and its `NLOPT_GN_*` algorithm family needs none at all.

**How hard is it to migrate from g2o to Ceres?**
Usually a few days for a moderate pipeline. The graph structure maps onto residual blocks, edges become cost functions, and the Jacobians you hand-wrote turn into automatic differentiation. The real work is re-validating that your robust kernels and convergence thresholds produce comparable results, not rewriting the problem definition.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
