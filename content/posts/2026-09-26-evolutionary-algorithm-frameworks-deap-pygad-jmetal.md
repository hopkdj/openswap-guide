---
title: "DEAP vs PyGAD vs jMetal in 2026: Which Evolutionary Framework Should You Actually Use?"
date: "2026-09-26"
tags: ["evolutionary-algorithms", "developer-libraries", "combinatorial-optimization", "python", "java"]
cover: "/img/screenshots/pygad-ga-lifecycle.jpg"
draft: false
---

Some problems refuse to behave. The objective has no gradient you can compute, the decision variables are discrete (which truck, which shift, which rack), and the only way to score a candidate solution is to run a simulation and look at the result. Gradient-based solvers are the wrong tool, brute force is exponential, and the honest answer is a **population-based search**: generate candidates, score them, breed the better ones, repeat.

That loop is simple enough to write in fifty lines — and full of enough subtle traps that thousands of teams have written a slightly broken version of it. The three frameworks worth considering in 2026 are **DEAP** (Python, 6,442 stars), **PyGAD** (Python, 2,225 stars) and **jMetal** (Java, 560 stars). They solve overlapping problems with sharply different philosophies, and picking the wrong one costs you either weeks of plumbing or a ceiling you hit at the first multi-objective problem.

## TL;DR — the 30-second verdict

- **Research-grade flexibility in Python, custom operators, genetic programming** → **DEAP**. LGPL-3.0, `pip install deap`, the `creator`/`toolbox` pattern that lets you swap every operator, plus a `gp.py` module for tree-based individuals.
- **Python, batteries included, callbacks and visualisation, model training adapters** → **PyGAD 3.7.0**. BSD-3-Clause, `pip install pygad`, one class with named parameters instead of a custom operator pipeline.
- **Multi-objective optimisation in Java, with benchmarking and Pareto-front tooling** → **jMetal 7.5**. MIT, Maven multi-module build, quality indicators and reference fronts shipped in the repository.
- **Do not** reach for these to solve a linear program, a routing problem with a published solver, or anything with a usable gradient. Our [numerical optimisation engines comparison](../2026-06-13-self-hosted-numerical-optimization-engines-ipopt-nlopt-ceres-pagmo2/) covers when a classical solver wins.

![The PyGAD genetic algorithm lifecycle, from the official PyGAD documentation](/img/screenshots/pygad-ga-lifecycle.jpg "The PyGAD genetic algorithm lifecycle: initial population, fitness evaluation, stop check, parent selection, crossover, mutation, and next-generation construction")

## The comparison table (data pulled 2026-09-26)

| Framework | Language | Latest version | Stars | Last push | Licence | Objective model | Parallelism |
|---|---|---|---|---|---|---|---|
| **DEAP** | Python | PyPI module (`pip install deap`) | 6,442 | 2026-04-17 | LGPL-3.0 | Single and multi-objective, GP, CMA-ES | Via `multiprocessing` / `toolbox.map` |
| **PyGAD** | Python | PyPI **3.7.0** | 2,225 | 2026-07-09 | BSD-3-Clause | Single and multi-objective callbacks | Wrapper-level control |
| **jMetal** | Java | **7.5** stable (master 7.6-SNAPSHOT) | 560 | 2026-09-10 | MIT | Multi-objective first, quality indicators | Dedicated `jmetal-parallel` module |

Read that table as a statement of intent rather than a ranking. DEAP has the largest community and the widest scope; PyGAD optimises for the shortest path from "I have a fitness function" to "I have a result and a chart"; jMetal is the only one of the three that treats multi-objective benchmarking — reference fronts, quality indicators, statistical comparison — as a first-class product.

## Which framework for which job

| Use case | Pick | Why |
|---|---|---|
| Custom operators, exotic encodings, genetic programming | **DEAP** | Nothing is hard-coded; `creator` and `toolbox` let you register your own types and operators |
| Teaching, prototyping, one-file scripts | **PyGAD** | A single class with named parameters, no pipeline to assemble |
| Parameter tuning where the objective is a simulation | **PyGAD** or **DEAP** | Both call a Python function and both handle integer and float genes |
| Two or more conflicting objectives (cost vs latency) | **jMetal** | NSGA-II/III, SPEA2, MOEA/D and friends with quality indicators built in |
| JVM application that cannot add a Python service | **jMetal** | Plain Maven dependency, no interpreter boundary |
| You need published benchmark comparisons | **jMetal** | Reference Pareto fronts and indicator utilities ship in the repository |
| Reproducible research on an encoding nobody has tried | **DEAP** | The operator registry documents exactly what ran |

## DEAP: the toolbox pattern, and why it is worth learning

```bash
pip install deap
```

DEAP does not give you an algorithm object. It gives you a **registry**. You declare what an individual is, what a population is, and which operator plays each role; the framework then runs the loop. This is the canonical one-max example, taken from `examples/ga/onemax.py` in the DEAP repository:

```python
import random

from deap import base
from deap import creator
from deap import tools

creator.create("FitnessMax", base.Fitness, weights=(1.0,))
creator.create("Individual", list, fitness=creator.FitnessMax)

toolbox = base.Toolbox()

# define 'attr_bool' to be an attribute ('gene') sampled from {0, 1}
toolbox.register("attr_bool", random.randint, 0, 1)

# define 'individual' to be a list of 100 'attr_bool' elements ('genes')
toolbox.register("individual", tools.initRepeat, creator.Individual,
    toolbox.attr_bool, 100)

# define the population to be a list of individuals
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

# the goal ('fitness') function to be maximized
def evalOneMax(individual):
    return sum(individual),

# register the goal / fitness function
toolbox.register("evaluate", evalOneMax)

# register the crossover operator
toolbox.register("mate", tools.cxTwoPoint)

# register a mutation operator with a probability to flip each gene of 0.05
toolbox.register("mutate", tools.mutFlipBit, indpb=0.05)

# selection: each individual is replaced by the best of three drawn at random
toolbox.register("select", tools.selTournament, tournsize=3)
```

The loop then reads almost like pseudocode — select, clone, cross with probability `CXPB`, mutate with probability `MUTPB`, and re-evaluate only the individuals whose fitness was invalidated:

```python
pop = toolbox.population(n=300)
CXPB, MUTPB = 0.5, 0.2

fitnesses = list(map(toolbox.evaluate, pop))
for ind, fit in zip(pop, fitnesses):
    ind.fitness.values = fit

for g in range(NGEN):
    offspring = toolbox.select(pop, len(pop))
    offspring = list(map(toolbox.clone, offspring))

    for child1, child2 in zip(offspring[::2], offspring[1::2]):
        if random.random() < CXPB:
            toolbox.mate(child1, child2)
            del child1.fitness.values
            del child2.fitness.values

    for mutant in offspring:
        if random.random() < MUTPB:
            toolbox.mutate(mutant)
            del mutant.fitness.values

    invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
    fitnesses = map(toolbox.evaluate, invalid_ind)
    for ind, fit in zip(invalid_ind, fitnesses):
        ind.fitness.values = fit

    pop[:] = offspring

best_ind = tools.selBest(pop, 1)[0]
```

The `del ind.fitness.values` idiom is the detail worth copying into any hand-rolled implementation: it marks an individual as dirty so the expensive evaluation runs once, not once per generation. Where DEAP earns its 6,442 stars is beyond that skeleton — the package also ships `algorithms.py` with ready-made drivers, `benchmarks/`, `cma.py` for CMA-ES, and `gp.py` for genetic programming with tree individuals. The repository's `examples/ga/` directory is a genuinely useful catalogue: `knapsack.py`, `nqueens.py`, `nsga2.py`, `nsga3.py`, and two model-training examples.

![A DEAP genealogy tree produced by the framework's own documentation](/img/screenshots/deap-genealogy.jpg "DEAP genealogy tree, an official DEAP documentation figure showing the ancestry of a single individual")

One licensing note that matters more than usual in Python: DEAP is **LGPL-3.0**, not MIT. Importing it normally is unproblematic, but if you fork it, modify it and ship the modified library, the copyleft terms apply. Check this before vendoring DEAP internals into a closed product.

## PyGAD: the shortest path from fitness function to result

```bash
pip install pygad
```

PyGAD inverts DEAP's design. Instead of registering operators, you write a fitness function with a fixed signature and pass named parameters to one class. Here is the example from the PyGAD repository, lightly trimmed:

```python
import numpy

function_inputs = [4, -2, 3.5, 5, -11, -4.7]
desired_output = 44

def fitness_func(ga_instance, solution, solution_idx):
    output = numpy.sum(solution * function_inputs)
    fitness = 1.0 / (numpy.abs(output - desired_output) + 0.000001)
    return fitness

num_generations = 100
num_parents_mating = 7
sol_per_pop = 50
num_genes = len(function_inputs)

ga_instance = pygad.GA(num_generations=num_generations,
                       num_parents_mating=num_parents_mating,
                       fitness_func=fitness_func,
                       sol_per_pop=sol_per_pop,
                       num_genes=num_genes)
ga_instance.run()

solution, solution_fitness, solution_idx = ga_instance.best_solution()
```

Three things justify choosing PyGAD over DEAP for a lot of real work. First, the callback surface is unusually complete — `on_start`, `on_fitness`, `on_parents`, `on_crossover`, `on_mutation`, `on_generation` and `on_stop` all exist, so progress reporting, early stopping and checkpointing are hook points rather than code you insert into a loop you own. Second, visualisation is a first-class extra:

```bash
pip install pygad[visualize]
```

Third, the package ships optional adapters for the ecosystem around it (`pip install pygad[deep_learning]`), which is the pragmatic reason many teams pick it: the same class that tunes a hyper-parameter vector can also drive the training loop that consumes it. PyGAD 3.7.0 was published in July 2026 under BSD-3-Clause, so there is no copyleft question at all — the most permissive licence in this comparison.

Where PyGAD is weaker is architectural freedom. If your encoding is a tree, a variable-length sequence or something with bespoke constraint repair, DEAP's registry will fit it more naturally than named-parameter configuration.

## jMetal: multi-objective optimisation as a discipline

```xml
<dependency>
    <groupId>org.uma.jmetal</groupId>
    <artifactId>jmetal-core</artifactId>
    <version>7.5</version>
</dependency>
```

jMetal's README states plainly that the last stable version is **7.5**, while `master` tracks 7.6-SNAPSHOT — and the changelog shows fixes and new algorithm variants landing in September 2026. The project is a Maven multi-module build: `jmetal-core` for the fundamental classes, `jmetal-algorithm` for the implementations, `jmetal-problem` for benchmark problems, `jmetal-lab` for experimentation and visualisation, `jmetal-parallel` for parallel extensions, `jmetal-auto` for automatic algorithm design, and `jmetal-component` for component-based algorithms.

Here is the real NSGA-II runner from the repository, `examples/multiobjective/nsgaii/NSGAIIRunner.java`, condensed to its essentials:

```java
String problemName = "org.uma.jmetal.problem.multiobjective.zdt.ZDT1";
String referenceParetoFront = "resources/referenceFrontsCSV/ZDT1.csv";

Problem<DoubleSolution> problem = ProblemFactory.<DoubleSolution>loadProblem(problemName);

double crossoverProbability = 0.9;
double crossoverDistributionIndex = 20.0;
CrossoverOperator<DoubleSolution> crossover = new SBXCrossover(crossoverProbability,
    crossoverDistributionIndex);

double mutationProbability = 1.0 / problem.numberOfVariables();
double mutationDistributionIndex = 20.0;
MutationOperator<DoubleSolution> mutation = new PolynomialMutation(mutationProbability,
    mutationDistributionIndex);

SelectionOperator<List<DoubleSolution>, DoubleSolution> selection = new BinaryTournamentSelection<>(
    new RankingAndCrowdingDistanceComparator<>());

int populationSize = 100;
Algorithm<List<DoubleSolution>> algorithm =
    new NSGAIIBuilder<>(problem, crossover, mutation, populationSize)
        .setSelectionOperator(selection)
        .setMaxEvaluations(25000)
        .build();

AlgorithmRunner algorithmRunner = new AlgorithmRunner.Executor(algorithm).execute();
List<DoubleSolution> population = algorithm.result();
```

The part to notice is the ending, because it is what the other two frameworks do not give you out of the box: `QualityIndicatorUtils.printQualityIndicators(...)` compares your resulting front against a **reference Pareto front** read from a CSV shipped inside the repository (`resources/referenceFrontsCSV/ZDT1.csv`). That is the difference between "my algorithm found some solutions" and "my algorithm's hypervolume is measurable and comparable to published numbers". jMetal also exposes `ZDT1`-style benchmark problems through a `ProblemFactory` keyed by class name, so switching problems is a one-string change.

If you would rather keep the analysis in Python, the repository now ships `scripts/plot_front.py` (static matplotlib output for 2D/3D fronts and parallel coordinates) and `scripts/plot_front_interactive.py` (an interactive Plotly viewer). jMetal writes `FUN.csv`, the scripts read it, and the visual verification loop stays short.

## Pitfalls that decide whether your run is meaningful

- **Count evaluations, not generations.** Fitness evaluations are almost always your real cost. A configuration that converges in 40 generations but uses a 500-individual population is more expensive than one that converges in 80 generations with 150. Optimise generations × population, and reuse cached evaluations wherever the objective is deterministic.
- **Cache the children you already scored.** Both frameworks support this via invalid-fitness marking (DEAP's `del ind.fitness.values`, PyGAD's internal invalidation). If your own loop re-evaluates an unchanged individual, you are paying twice for the same number.
- **Seed the run and record the seed.** `random.seed(64)` in a notebook is not reproducibility. Record the seed, the framework version, the operator probabilities and the evaluation budget together — a result without those five numbers cannot be reproduced.
- **Do not turn a multi-objective problem into a weighted sum.** Picking weights up front hides the trade-off you were trying to explore. If two objectives genuinely conflict, produce a front (NSGA-II, SPEA2) and decide afterwards.
- **Operator choice is not interchangeable.** SBX and polynomial mutation assume bounded continuous variables; two-point crossover assumes a fixed-length sequence; flip-bit assumes binary. Choosing the convenient operator for the wrong encoding is the most common way to get a run that executes cheerfully and searches badly.
- **Watch diversity collapse.** Tournament selection with a large tournament size and heavy elitism converge fast and then stop improving. Track population diversity, not just the best fitness, or you will read a plateau as a solution.
- **Know the difference between keeping parents and keeping elites.** These are not synonyms: keeping the previous generation preserves diversity, keeping only the best few preserves quality. Whichever you configure, write it down — the two produce different results at the same evaluation count.
- **Constraints need an explicit strategy.** Penalty terms, repair operators and feasibility rules give different behaviour. A penalty weight that works at 10 variables can be irrelevant at 200.
- **Licence review, once.** DEAP is LGPL-3.0 (copyleft on modifications), PyGAD is BSD-3-Clause, jMetal is MIT. If you plan to ship a modified framework, this is the first thing to check, not the last.
- **Benchmark on your problem, not on the leaderboard.** ZDT and DTLZ results tell you a framework is implemented correctly. They tell you nothing about your 12-hour job-shop simulation, which is where the run either pays for itself or does not.

## Why self-host your search infrastructure

Evolutionary workloads are embarrassingly parallel and extremely easy to outsource by accident: each candidate evaluation is a function call, and it is tempting to send it to a hosted endpoint. The problem is that the fitness function usually encodes your business logic — dispatch rules, pricing, capacity limits, simulation models — and shipping it out means shipping your operational constraints out with it.

Keeping the search local has three concrete benefits. You get unlimited evaluations against your own hardware instead of a metered quota, which changes how you design the search rather than forcing you to shrink it. You get exact reproducibility, because framework version, seed and operator probabilities all stay pinned in your own image. And you get the ability to fuse the search with systems you already run — a staging database, a solver binary, an internal simulation service. If your search is really a constraint problem underneath, the [SAT solver comparison](../2026-09-25-sat-solvers-cadical-vs-kissat-vs-cryptominisat/) covers the exact-satisfaction side, and if it is a routing problem, the [vehicle routing optimisation overview](../2026-06-16-self-hosted-vehicle-routing-optimization-vroom-jsprit-ortools/) covers the purpose-built solvers that often beat a general framework outright.

## FAQ

**Which framework should a Python user start with in 2026?**
Start with PyGAD if your problem fits its parameter model — you will have a result and a fitness chart in an afternoon. Move to DEAP when you need a custom encoding, a custom operator, or tree-based individuals, and accept the extra wiring in exchange for control.

**Is DEAP still maintained?**
Yes, though its cadence is slower than PyGAD's: the repository was last pushed 2026-04-17, versus 2026-07-09 for PyGAD. DEAP's scope and stability are why it remains the most-starred framework in this comparison at 6,442 stars, and its algorithm set covers cases the others do not.

**When is a Java framework the right answer?**
When your objective function lives in a JVM service — an existing risk engine, a simulation written in Java, or a Spring application — and calling across a process boundary would dominate the run time. jMetal 7.5 is MIT-licensed and installs as an ordinary Maven dependency.

**How do I handle constraints?**
Decide the strategy before you tune parameters: penalty terms are the simplest and most sensitive to scaling; repair operators are more reliable when a feasible solution is easy to construct from an infeasible one; feasibility rules (prefer feasible, then compare objective) work well when feasible solutions are common. jMetal's problem interfaces carry objective and constraint values separately, which makes the choice explicit.

**Do I need a GPU?**
No. These are CPU-bound frameworks and most published applications run on ordinary servers. Throughput comes from evaluating candidates in parallel across cores or machines — memory bandwidth and your simulation cost are the real limits.

**Can I compare frameworks fairly?**
Only on your own problem, at equal evaluation counts. Run each framework to the same budget, with tuned operator probabilities for each, and compare best-found fitness — plus a random-search baseline to prove the search is doing anything at all.

**How many parameters do I need to tune?**
Fewer than you think, and the important ones are structural: population size, selection pressure, crossover and mutation probability, and elitism. Log every configuration with its seed; a result you cannot reproduce is an anecdote.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "DEAP vs PyGAD vs jMetal in 2026: Which Evolutionary Framework Should You Actually Use?",
  "description": "Practical comparison of open-source evolutionary algorithm frameworks in 2026: DEAP, PyGAD and jMetal, with real versions, star counts, operator registries and multi-objective benchmarking guidance.",
  "datePublished": "2026-09-26",
  "dateModified": "2026-09-26",
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
