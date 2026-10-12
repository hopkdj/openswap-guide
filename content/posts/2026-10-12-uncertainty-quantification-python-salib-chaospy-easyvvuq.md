---
title: "Uncertainty Quantification in Python in 2026: SALib vs Chaospy vs EasyVVUQ"
date: "2026-10-12"
tags: ["uncertainty-quantification", "scientific-computing", "python", "sensitivity-analysis", "simulation"]
draft: false
cover: "/img/screenshots/salib-heatmap.jpg"
---

Your model has eleven input parameters, four of which are measured with 15 per cent error, and you have been reporting a single deterministic number — a mean from one run at nominal values — as if it were a prediction. That is the most common methodological failure in computational engineering, and it is a statistics problem, not a modelling problem. Uncertainty quantification (UQ) is the discipline of propagating input uncertainty to output uncertainty, and decomposing which inputs actually drive the spread.

In Python, three libraries dominate that workflow: **SALib** for sensitivity analysis, **Chaospy** for polynomial chaos expansions, and **EasyVVUQ** for running UQ campaigns against black-box simulation codes on HPC. They are complementary more often than they are competitors — and picking them by star count alone is a reliable way to end up rebuilding the missing third yourself.

## The Short Version (TL;DR)

- **"Which of my 15 parameters actually matter?" → SALib.** It implements Sobol, Morris, FAST, Delta, DGSM and PAWN behind one consistent interface, with bootstrap confidence intervals. Screening and variance decomposition are what it does best.
- **"I need a surrogate model and analytic moments, not just rankings" → Chaospy.** Polynomial chaos expansion gives you a cheap emulator, output moments, and sensitivity indices derived from coefficients rather than sampled estimates.
- **"My model is a Fortran binary on a cluster and I need 10,000 runs with provenance" → EasyVVUQ.** Its campaign/encoder architecture wraps external executables, and its analysis layer stores everything in a queryable database.
- **If you only adopt one: SALib.** It is the fastest path from "I have a model" to "I know which parameters to measure better", and it is the most actively maintained of the three (last repository activity October 2026).

## Feature Comparison at a Glance

Project statistics read live from GitHub at publish time.

| Dimension | SALib | Chaospy | EasyVVUQ |
|---|---|---|---|
| GitHub stars | **1,015** | **480** | **105** |
| License | MIT | MIT | LGPL-3.0 |
| Last repository activity | 2026-10-11 | 2025-09-04 | 2026-10-09 |
| Install | `pip install SALib` | `pip install chaospy` | `pip install easyvvuq` |
| Primary role | Sensitivity analysis | Spectral uncertainty propagation | UQ campaign orchestration (VVUQ) |
| Core methods | Sobol, Morris, FAST, Delta, DGSM, PAWN, fractional factorial | Polynomial chaos, Gaussian/sparse-grid quadrature, regression, pseudo-spectral | Sampling + encoder wrappers + PCE/MC analysis |
| Model interface | Python callable | Python callable | External executables via input templates |
| Confidence intervals built in | **Yes (bootstrap)** | Via sampling | Via analysis results |
| HPC / scheduler support | Manual | Manual | **Dask, SLURM jobqueue, cloud backends** |
| Persistent provenance store | No | No | **Yes (campaign database)** |
| Steepest learning curve | Low | Medium-high | Medium |

## Which Tool for Which Job

| Use case | Pick | Why |
|---|---|---|
| Screening 20 parameters down to the 5 that matter | SALib | Morris and DGSM are designed for cheap factor screening at a fraction of Sobol's sampling cost |
| Formal variance decomposition with confidence intervals | SALib | `sobol.analyze` returns first-order, total-order and second-order indices with bootstrap CIs |
| Building a fast surrogate of an expensive model | Chaospy | Polynomial chaos expansion is a surrogate that also delivers analytic moments |
| Analytic output mean and variance from an expansion | Chaospy | Moments come from expansion coefficients, no extra model evaluations needed |
| Driving a compiled simulator with file-based input | EasyVVUQ | `GenericEncoder` + template substitution handle black-box binaries cleanly |
| Thousands of HPC runs with resumable provenance | EasyVVUQ | Campaigns persist to a database; Dask and SLURM backends are built in |
| Teaching UQ concepts quickly | SALib | Two functions, one problem dictionary, an immediate result |
| Correlated or non-uniform input distributions | Chaospy | Arbitrary joint distributions and custom copulas are first-class concepts |

## SALib: Screening and Variance Decomposition

SALib (1,015 stars, MIT) is the library to reach for first, because the highest-value question in any UQ study is not "what is the output distribution" but "which inputs should I spend money measuring better". Its method coverage maps directly onto famous papers: Sobol for variance decomposition, Morris for screening, FAST for frequency-based decomposition, Delta and PAWN for distribution-based sensitivity.

The modern entry point is `ProblemSpec`, which chains sampling, evaluation and analysis in one fluent expression:

```python
from SALib import ProblemSpec

sp = ProblemSpec({
    "names": ["a", "q", "b"],
    "bounds": [[0.0, 0.1], [2.0, 4.5], [0.1, 0.45]],
})

(sp.sample_sobol(1024)
   .evaluate(model_function)
   .analyze_sobol())

print(sp.analysis.to_df())
```

The classic procedural API is equally valid and is what you will find in most published example code:

```python
from SALib.sample import saltelli
from SALib.analyze import sobol

problem = {
    "num_vars": 3,
    "names": ["a", "q", "b"],
    "bounds": [[0.0, 0.1], [2.0, 4.5], [0.1, 0.45]],
}

param_values = saltelli.sample(problem, 1024)   # N * (2D + 2) model runs
Y = model_function(param_values)
Si = sobol.analyze(problem, Y, print_to_console=False)

print(Si["S1"], Si["ST"], Si["S1_conf"])
```

Read that sampling formula carefully, because it is where most UQ budgets die: **Saltelli sampling needs N × (2D + 2) model evaluations for D parameters.** At 20 parameters and N = 1024 that is 43,008 runs. This is exactly why Morris screening exists — a few dozen trajectories can tell you which parameters to drop before you commit to the expensive decomposition. Run screening first, then Sobol on the survivors, and you will finish the study.

![Sobol sensitivity heatmap produced by the SALib documentation examples](/img/screenshots/salib-heatmap.jpg)

Always report the bootstrap confidence intervals (`S1_conf`, `ST_conf`) rather than bare indices. A parameter whose total-order index is 0.05 with a confidence interval of ±0.06 is not "weakly influential" — it is **undetermined at your sample size**, and saying so is the honest result.

## Chaospy: Polynomial Chaos and Cheap Surrogates

Chaospy (480 stars, MIT) sits at a different level of the stack. Where SALib treats the model as a callable to be sampled, Chaospy treats the model as an operator to be *approximated* by a polynomial expansion in the input random variables. That expansion — polynomial chaos — is simultaneously a surrogate model, a moment calculator, and a sensitivity analyser.

```python
import chaospy

# define the joint input distribution
distribution = chaospy.J(chaospy.Uniform(0, 1), chaospy.Normal(0, 1))

# generate quadrature nodes and weights
nodes, weights = chaospy.generate_quadrature(3, distribution, rule="gaussian")

# evaluate the model at the nodes and fit an expansion
evals = model_function(nodes)
expansion = chaospy.generate_expansion(3, distribution)
model_approx = chaospy.fit_regression(expansion, nodes, evals)

# the surrogate is now cheap: sample it a million times
samples = distribution.sample(1000000)
surrogate_outputs = model_approx(*samples)
print("mean:", surrogate_outputs.mean(), "std:", surrogate_outputs.std())
```

The economics are compelling when model runs are expensive. A handful of quadrature nodes plus a regression fit can yield a surrogate that costs microseconds to evaluate, so you can compute output distributions, tail probabilities and sensitivity indices from **millions** of surrogate evaluations instead of thousands of simulator runs. Sensitivity indices fall straight out of the expansion coefficients, which also makes them effectively noise-free compared with sampled estimates.

Two cautions. First, polynomial chaos is not free of the curse of dimensionality: expansion terms grow combinatorially with parameter count and polynomial order, so 30 input parameters will punish you regardless of how clever the quadrature rule is — that is a screening problem, and SALib is the tool for it. Second, Chaospy is a **mathematical library, not a workflow engine**: it will not run your simulator, version your inputs, or resume a crashed batch. You supply the loop.

Its visible repository activity is the oldest of the three (September 2025), so evaluate maintenance risk against your project's lifespan. The mathematics it implements is decades-stable, which mitigates that considerably.

## EasyVVUQ: Campaigns for Black-Box Codes on Clusters

EasyVVUQ (105 stars, LGPL-3.0) solves the problem the other two ignore entirely: **running thousands of coupled simulations of an external code with reproducible provenance**. Instead of importing your model as a Python function, you describe an application, attach an encoder that writes its input files from a template, and let a campaign manage sampling, execution, storage and analysis.

```python
import chaospy as cp
import easyvvuq as uq

campaign = uq.Campaign(name='gauss', work_dir=".")

params = {
    "sigma": {"type": "float", "min": 0.0, "max": 100000.0, "default": 20000.0},
    "mu": {"type": "float", "min": 0.0, "max": 100000.0, "default": 100000.0},
}

encoder = uq.encoders.GenericEncoder(
    template_fname='gauss.template',
    target_filename='input.json',
)

campaign.add_app(name="gauss", params=params, encoder=encoder)

vary = {"sigma": cp.Uniform(100.0, 300.0), "mu": cp.Uniform(50000.0, 200000.0)}
sampler = uq.sampling.RandomSampler(vary=vary)
campaign.set_sampler(sampler)
campaign.draw_samples(32)
```

The architectural payoff shows up later than the first run and matters more than it. Every sample, input file, run and result lands in a **campaign database**, so a 10,000-sample study is queryable, resumable and auditable — you can ask which samples completed, rerun only the failures, and hand a reviewer a record of exactly which parameters produced which result. Named analysis classes then consume the campaign directly, and Dask or SLURM jobqueue backends distribute execution across a cluster.

Its trade-offs are the mirror image of Chaospy's. The learning curve is real (encoders, app definitions and campaign lifecycle), the community is small at 105 stars, and LGPL-3.0 licensing may need a legal glance in closed-source industrial settings. But among the three it is the only one built for the situation where the model is not a Python function — which, in engineering practice, is the normal case.

## Using All Three Together

The mature pattern is a pipeline: screen cheaply, then expand, then scale.

```python
# Step 1 — SALib: screen 12 parameters down to the 5 that matter
from SALib.analyze import morris
Si_morris = morris.analyze(problem, X, Y_morris)
important = [problem["names"][i] for i, mu in enumerate(Si_morris["mu_star"])
             if mu > threshold]

# Step 2 — Chaospy: build a polynomial chaos surrogate on the survivors
import chaospy
distribution = chaospy.J(*[chaospy.Uniform(*b) for b in selected_bounds])

# Step 3 — EasyVVUQ: run the HPC campaign and keep provenance
# campaign.draw_samples(N); campaign.execute(); campaign.collate()
```

Screening with Morris at a few hundred runs, expanding the surviving parameters with polynomial chaos, then executing the production campaign under a workflow manager is how teams get defensible UQ results inside a realistic compute budget instead of blowing a month of cluster time on an under-sampled Sobol study.

## Installing All Three

All three install from PyPI, and Chaospy plus SALib are on conda-forge:

```bash
pip install SALib chaospy easyvvuq

# conda-forge equivalents
conda install -c conda-forge salib chaospy
```

For reproducibility, pin the environment in a container and mount your model directory read-only so a runaway campaign cannot overwrite source data:

```yaml
# docker-compose.yml — reproducible UQ sandbox
services:
  uq:
    image: python:3.12-slim
    working_dir: /work
    volumes:
      - ./study:/work
      - ./model:/model:ro
    command: >
      bash -lc "pip install --no-cache-dir SALib chaospy easyvvuq &&
      python run_study.py"
```

## Where Teams Get Burned

- **Under-sampled Sobol studies.** Sobol indices at N = 64 with confidence intervals wider than the indices themselves get published anyway. Check `S1_conf` before you check `S1`.
- **Screening last instead of first.** Running full variance decomposition on 20 parameters is a budget mistake; Morris screening exists to cut the parameter list first.
- **Naive Monte Carlo for rare events.** Estimating a failure probability of 1e-4 by brute-force sampling needs millions of runs. Surrogate methods, importance sampling or subset simulation are the answer, not more CPU hours.
- **Correlated inputs.** Variance decomposition assumes independent inputs. Real measured parameters are often correlated; either de-correlate via a transformation or accept that your indices are approximate.
- **Fitting and validating a surrogate on the same samples.** Polynomial chaos expansions need held-out evaluation points. Report surrogate error, not just surrogate-predicted uncertainty — the latter can be confidently wrong.
- **Ignoring the polynomial order trade-off.** Too low and the surrogate misses nonlinearity; too high and expansion terms explode. Test convergence by increasing order until the moments stabilise.
- **Confusing parameter uncertainty with model error.** Accounting for noisy inputs while assuming your governing equations are exact understates total uncertainty and produces over-confident intervals.
- **No fixed random seed.** Sampling-based UQ without a recorded seed is not reproducible, which undermines the entire audit trail you built the campaign to create.

## Why Keep UQ Runs On Your Own Infrastructure

A UQ study is defined by its model evaluations: tens of thousands of runs of a simulator that may itself be proprietary, export-controlled, or licensed per-core. Uploading that simulator to a hosted platform is frequently impossible for contractual reasons, and per-run cloud pricing scales badly when the workload is deliberately thousands of executions. All three libraries are open source, install from public indexes, and impose no external service dependency, so the whole campaign — inputs, runs, results and database — can live on a workstation or a lab cluster you already operate.

To go further, our guides on [watershed hydrology modelling](../2026-06-12-self-hosted-watershed-hydrology-modeling-swat-parflow-vic/) and [nuclear engineering simulation](../2026-06-10-self-hosted-nuclear-engineering-openmc-openmoc-moltres/) show the class of models these campaigns typically drive, [electrochemical impedance spectroscopy tooling](../2026-06-13-self-hosted-electrochemical-impedance-spectroscopy-impedance-py-pyeis-deareis/) covers a domain where parameter uncertainty directly changes conclusions, and the [scientific data visualization stacks](../2026-06-09-self-hosted-scientific-data-visualization-paraview-visit-vtkjs-pyvista/) guide covers presenting the resulting ensembles.

## FAQ

**What is the difference between sensitivity analysis and uncertainty quantification?**

Uncertainty quantification asks how input uncertainty propagates to output uncertainty — it produces distributions, moments and confidence intervals. Sensitivity analysis asks which inputs are responsible for that spread. In practice you do both: quantify the output distribution, then decompose the variance to find which parameters to measure more precisely or control more tightly.

**Do I need Chaospy if I already use SALib?**

Not always. SALib covers screening and variance decomposition thoroughly and is simpler to adopt. Add Chaospy when you specifically need a surrogate model, analytic output moments, or support for arbitrary and correlated input distributions that SALib's sampling approach does not model directly. Many studies use SALib alone and are perfectly defensible.

**Can these libraries drive a compiled simulator rather than a Python function?**

SALib and Chaospy expect a Python callable, which means you usually wrap the simulator in a subprocess call yourself. EasyVVUQ is built for the opposite situation: it defines applications, encodes parameters into input templates, executes external codes, and records the results in a campaign database. For a Fortran or C binary on a cluster, EasyVVUQ removes the wrapping work you would otherwise write by hand.

**How many model runs does a Sobol analysis need?**

Saltelli sampling generates N × (2D + 2) evaluations for D parameters, so the total grows linearly in the base sample size N and linearly in parameter count. Start with Morris screening to reduce D, then choose N by checking that bootstrap confidence intervals on the indices are acceptably narrow — not by picking a round number like 1024 and hoping.

**Is polynomial chaos worth it over plain Monte Carlo?**

When each model run is expensive, yes. A well-fitted expansion needs far fewer simulator evaluations than Monte Carlo for comparable accuracy on the moments, and once fitted it can be sampled millions of times at negligible cost. For cheap models with many parameters, plain sampling plus a screening method is usually the more economical choice.

**Are these libraries suitable for HPC clusters?**

EasyVVUQ is explicitly designed for it, with Dask and SLURM jobqueue backends and campaign persistence so failed runs can be rerun individually. SALib and Chaospy are single-process libraries: you generate the sample matrix yourself and distribute it with whatever scheduler you already use, then collate results for analysis.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Uncertainty Quantification in Python in 2026: SALib vs Chaospy vs EasyVVUQ",
  "description": "A practical 2026 comparison of SALib, Chaospy and EasyVVUQ for uncertainty quantification and sensitivity analysis in Python, with real code, feature tables and production pitfalls.",
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
