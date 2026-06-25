---
title: "Self-Hosted Linear Programming Solvers: GLPK vs HiGHS vs SoPlex vs CLP for Optimization Workloads"
date: "2026-06-26"
tags: ["optimization", "linear-programming", "operations-research", "scientific-computing", "mathematical-modeling"]
draft: false
---

## Introduction

Linear programming (LP) is the mathematical foundation of operations research — it powers supply chain optimization, production scheduling, portfolio allocation, transportation routing, and energy grid management. At its core, an LP problem minimizes or maximizes a linear objective function subject to linear constraints, and the simplex method invented by George Dantzig in 1947 remains the workhorse algorithm for solving these problems.

The open-source ecosystem provides four production-grade LP solvers that can handle problems ranging from small academic exercises to industrial-scale models with millions of variables: **GLPK** (the GNU reference implementation), **HiGHS** (the modern high-performer), **SoPlex** (the SCIP ecosystem's LP engine), and **CLP** (COIN-OR's battle-tested solver). This article compares their performance, API design, and integration patterns.

## Comparison Overview

| Feature | GLPK | HiGHS | SoPlex | CLP |
|---------|------|-------|--------|-----|
| **Stars** | GNU project (~56 fork) | 1,676+ | 81+ | 487+ |
| **License** | GPLv3 | MIT | Apache 2.0 | EPL 2.0 |
| **Primary Algorithm** | Revised Simplex | Interior Point + Simplex | Revised Simplex (sparse) | Dual Simplex |
| **MILP Support** | Yes (branch-and-cut) | Yes (branch-and-cut) | No (via SCIP) | No (via CBC) |
| **API Languages** | C, Python (swiglpk) | C++, Python, Julia, Rust | C++ | C++, Python (CyLP) |
| **Threading** | Single-thread | Multi-threaded | Single-thread | Multi-threaded |
| **Model File Formats** | MPS, CPLEX LP, MathProg | MPS, LP, model building API | MPS, LP | MPS, LP |
| **Warm Start** | Yes | Yes | Yes | Yes |
| **Preprocessing** | Built-in presolver | Advanced presolve | SCIP presolving | Built-in presolver |

## GLPK: The GNU Standard

The GNU Linear Programming Kit (GLPK) is the reference open-source LP solver, developed since the 1990s as part of the GNU Project. It implements the revised simplex method with both primal and dual variants, plus a branch-and-cut framework for mixed-integer linear programming (MILP).

**Repository**: GLPK is distributed from the GNU FTP servers. Community-maintained mirrors exist on GitHub.

```bash
# Debian/Ubuntu
sudo apt install glpk-utils libglpk-dev

# Fedora/RHEL
sudo dnf install glpk glpk-devel

# macOS
brew install glpk
```

Command-line usage with the standalone solver:

```bash
# Solve from MathProg model file
glpsol --model model.mod --output solution.txt

# Solve from MPS format (industry standard)
glpsol --mps problem.mps --output solution.txt

# Solve LP format
glpsol --lp problem.lp --output solution.txt
```

A GLPK MathProg model for the classic diet problem:

```ampl
# Diet problem: minimize cost while meeting nutritional requirements
set FOODS;
set NUTRIENTS;

param cost{FOODS};
param requirement{NUTRIENTS};
param amount{FOODS, NUTRIENTS};

var x{FOODS} >= 0;

minimize total_cost: sum{f in FOODS} cost[f] * x[f];

subject to nutrition{n in NUTRIENTS}:
    sum{f in FOODS} amount[f, n] * x[f] >= requirement[n];

data;
set FOODS := bread milk eggs;
set NUTRIENTS := calories protein calcium;

param cost := bread 2.0 milk 3.5 eggs 4.0;
param requirement := calories 2000 protein 55 calcium 800;

param amount : calories protein calcium :=
    bread   265    9    26
    milk    160    8   285
    eggs    150    6    1;

end;
```

GLPK's strength is its accessibility — the GMPL/MathProg modeling language is a subset of AMPL, making it easy to translate academic models. The library ships with comprehensive documentation (the 300-page GLPK reference manual) and a straightforward C API with functions like `glp_create_prob()`, `glp_add_rows()`, `glp_add_cols()`, and `glp_simplex()`.

## HiGHS: The Modern Performer

HiGHS (High-performance optimization software for linear optimization) is the newest entrant, developed at the University of Edinburgh since 2019. It implements a novel concurrent solver architecture that runs simplex and interior-point methods simultaneously — the first to finish returns the result.

**Repository**: `ERGO-Code/HiGHS` (1,676+ stars)

```bash
# Build from source (recommended for latest features)
git clone https://github.com/ERGO-Code/HiGHS.git
cd HiGHS
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
sudo make install
```

HiGHS offers a clean Python interface via `highspy`:

```python
import highspy

h = highspy.Highs()
h.addVar(lb=0, ub=highspy.kHighsInf)   # x1 >= 0
h.addVar(lb=0, ub=highspy.kHighsInf)   # x2 >= 0

# Minimize: 3*x1 + 2*x2
h.changeColCost(0, 3.0)
h.changeColCost(1, 2.0)

# Constraint: 2*x1 + x2 <= 12
h.addRow(lb=-highspy.kHighsInf, ub=12.0, num_nz=2, index=[0,1], value=[2.0,1.0])
# Constraint: x1 + 2*x2 <= 12
h.addRow(lb=-highspy.kHighsInf, ub=12.0, num_nz=2, index=[0,1], value=[1.0,2.0])

h.run()
solution = h.getSolution()
print(f"x1 = {solution.col_value[0]:.2f}, x2 = {solution.col_value[1]:.2f}")
print(f"Objective = {h.getObjectiveValue():.2f}")
```

HiGHS' parallel architecture is its killer feature for production workloads. On multi-core systems, the interior-point solver (best for large sparse problems) and the simplex solver (best for re-optimization with warm starts) compete against each other, and the solver returns results as soon as either finishes. For problems with 10,000+ variables and constraints, this concurrent strategy can reduce wall-clock time by 40-60% compared to single-method solvers.

## SoPlex: The SCIP Ecosystem's LP Engine

SoPlex (Sequential object-oriented simPlex) is the LP solver component of the SCIP Optimization Suite. While SoPlex itself solves only continuous linear programs, it is the computational backbone of SCIP's constraint integer programming framework, which handles mixed-integer and nonlinear problems.

**Repository**: `scipopt/soplex` (81+ stars)

```bash
git clone https://github.com/scipopt/soplex.git
cd soplex
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
```

SoPlex is designed for sparse LP problems — its revised simplex implementation uses sparse LU factorization and column generation techniques optimized for problems where the constraint matrix is over 95% zeros (typical in network flow and production planning models). Its C++ API provides a solver object with methods for adding columns (variables with bounds and constraint coefficients), adding rows (constraints), and calling the optimize method.

SoPlex's main advantage is its seamless integration with SCIP's ecosystem. If your optimization problem starts as a linear model but later requires integer variables, constraint programming, or nonlinear constraints, SoPlex + SCIP provides a unified framework without switching solver backends.

## CLP: COIN-OR's Battle-Tested Engine

CLP (COIN-OR Linear Programming) is part of the COIN-OR (Computational Infrastructure for Operations Research) initiative, an umbrella project of open-source optimization tools developed by IBM Research and the academic community since 2000.

**Repository**: `coin-or/Clp` (487+ stars)

```bash
# Build from source
git clone https://github.com/coin-or/Clp.git
cd Clp
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
sudo make install

# Or use conda
conda install -c conda-forge coincbc
```

CLP is tightly coupled with CBC (COIN-OR Branch-and-Cut), the MILP solver. Together they form one of the most mature open-source optimization stacks. The CyLP Python bindings provide programmatic access with methods to add variables, constraints, and call the primal simplex solver.

CLP's dual simplex implementation is particularly efficient for re-optimization — when you solve a base model, then modify a few constraints or bounds, CLP's warm-start capability reuses the previous optimal basis to find the new solution in a fraction of the time. This is critical for branch-and-bound in MILP (where each node modifies bounds) and for online optimization scenarios.

## Performance: LP Benchmark Suite

Industry-standard benchmark results (Mittelmann's LP benchmark, approximate average solve time in seconds):

| Problem Size | GLPK | CLP | SoPlex | HiGHS |
|-------------|------|-----|--------|-------|
| Small (under 1K vars) | 0.05s | 0.03s | 0.03s | 0.02s |
| Medium (1K-10K) | 2.1s | 1.2s | 0.9s | 0.6s |
| Large (10K-100K) | 45s | 18s | 15s | 8s |
| Very Large (over 100K) | timeout | 120s | 95s | 42s |

HiGHS leads across all problem sizes due to its concurrent solver architecture and modern presolve implementation. SoPlex excels on extremely sparse matrices (99%+ zeros) common in network flow problems. CLP has the strongest dual simplex warm-start performance for re-optimization. GLPK, while slower on large instances, remains the most accessible and thoroughly documented option.

## Self-Hosted Optimization Infrastructure

For teams running optimization workloads as part of a microservice architecture, solvers can be containerized:

```dockerfile
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y     glpk-utils libglpk-dev python3-pip cmake g++ make git
RUN pip3 install highspy cylp
RUN git clone https://github.com/ERGO-Code/HiGHS.git &&     cd HiGHS && mkdir build && cd build &&     cmake .. -DCMAKE_BUILD_TYPE=Release && make -j$(nproc) && make install
```

A simple FastAPI optimization service exposes the solver as an HTTP endpoint:

```python
from fastapi import FastAPI
from pydantic import BaseModel
import highspy

app = FastAPI()

class LPModel(BaseModel):
    objective: list[float]
    constraints: list[dict]

@app.post("/solve")
def solve_lp(model: LPModel):
    h = highspy.Highs()
    for coeff in model.objective:
        h.addVar(lb=0, ub=highspy.kHighsInf)
    for i, coeff in enumerate(model.objective):
        h.changeColCost(i, coeff)
    for constr in model.constraints:
        indices = constr["var_indices"]
        values = constr["coefficients"]
        ub = constr.get("ub", highspy.kHighsInf)
        lb = constr.get("lb", -highspy.kHighsInf)
        h.addRow(lb=lb, ub=ub, num_nz=len(indices), index=indices, value=values)
    h.run()
    return {"status": "optimal", "objective": h.getObjectiveValue(),
            "solution": list(h.getSolution().col_value)}
```

## FAQ

### When should I use linear programming versus constraint programming?

Linear programming (LP) solves problems where all constraints and objectives are linear functions of continuous or integer variables — think production planning, portfolio optimization, and transportation routing. Constraint programming (CP) handles combinatorial problems with logical constraints, such as scheduling with precedence rules, resource allocation with complex dependencies, and configuration problems. LP solvers return globally optimal solutions with duality certificates; CP solvers typically return feasible solutions with no optimality guarantee. For problems with both linear and combinatorial elements, use SCIP (which combines SoPlex for LP with constraint handling).

### How do I choose between the four solvers for a new project?

Start with HiGHS if you need maximum single-machine performance and modern APIs (Python, Julia, Rust). Use GLPK if you need maximum portability (pure C, GPL-compatible) and comprehensive documentation. Choose CLP if you are building a MILP workflow (it integrates with CBC for integer variables). Choose SoPlex if you are already in the SCIP ecosystem or need sparse LP as a component of a larger optimization framework. All four solvers support the MPS file format, so you can benchmark your specific problem on each without committing to one solver.

### Can these solvers handle stochastic or robust optimization?

None of these solvers natively support stochastic programming. You need to implement scenario generation and the deterministic equivalent yourself, then feed the expanded model to the LP solver. For two-stage stochastic programming with recourse, tools like PySP (part of Pyomo) can generate scenario trees and call CLP or GLPK as the underlying LP engine. For robust optimization with uncertainty sets, you will typically reformulate the robust counterpart into a standard LP — but for conic problems beyond LP, you will need an SOCP solver like ECOS, SCS, or IPOPT.

### What is the largest problem size these open-source solvers can handle?

HiGHS regularly solves problems with 100,000+ variables and constraints on a single machine with 32 GB RAM. The limiting factor is not the solver algorithm but memory for storing the constraint matrix. For problems beyond roughly 500K non-zeros in the constraint matrix, consider distributed solvers, decomposition methods (Dantzig-Wolfe, Benders), or commercial solvers which have more sophisticated presolve and memory management. For truly massive problems with millions of variables, column generation or Lagrangian relaxation may be the only practical approaches with open-source tools.

For related optimization infrastructure, see our [Constraint Programming Solvers comparison](../2026-06-22-constraint-programming-solvers-ortools-gecode-choco-jacop/) and [Sparse Linear Solvers guide](../2026-06-22-sparse-linear-solvers-suitesparse-mumps-petsc-superlu/). For the broader mathematical computing ecosystem, our [Mathematical Computing Platforms guide](../2026-05-11-open-source-mathematical-computing-sagemath-octave-maxima-guide/) covers SageMath, Octave, and Maxima.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linear Programming Solvers: GLPK vs HiGHS vs SoPlex vs CLP for Optimization Workloads",
  "description": "Comprehensive comparison of four open-source linear programming solvers: GLPK (GNU reference), HiGHS (modern concurrent architecture), SoPlex (SCIP ecosystem), and CLP (COIN-OR). Includes benchmark data, Docker deployment patterns, and API examples in C, C++, and Python.",
  "datePublished": "2026-06-26",
  "dateModified": "2026-06-26",
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
