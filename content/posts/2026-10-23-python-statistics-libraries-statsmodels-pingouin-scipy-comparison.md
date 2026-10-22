---
title: "statsmodels vs Pingouin vs SciPy in 2026: Which Python Statistics Library Should You Actually Use?"
date: "2026-10-23"
tags: ["python", "statistics", "data-analysis", "statsmodels", "scipy", "pingouin"]
draft: false
cover: "/img/screenshots/statsmodels-logo.jpg"
description: "Practical 2026 comparison of statsmodels, Pingouin and SciPy.stats: which library to use for regression, ANOVA, effect sizes, multiple comparisons and time series, with real code and version pitfalls."
---

You have a DataFrame with two groups, a p-value, and a reviewer asking for the effect size, the confidence interval, and the corrected p-value for the other nine tests you ran. You can chain four `scipy.stats` calls and hand-roll the corrections — or you can use the one library that returns all of it in a single tidy row.

Python has three serious statistics libraries and they are **not** interchangeable. **SciPy** ships the distributions and the primitive tests. **statsmodels** ships the models — regression, mixed effects, time series, econometrics. **Pingouin** ships the *reporting layer* that applied researchers actually need. Most analyses end up importing two of the three, and picking the wrong pair wastes days.

## TL;DR — the 30-second verdict

- **Hypothesis tests with effect sizes, power and corrections in one call**: use **Pingouin** (1,937★, GPL-3.0, pushed 2026-10-17). `pg.ttest()` returns T, dof, p-value, 95% CI, Cohen's d, achieved power and a Bayes factor in a single DataFrame row.
- **Regression, mixed models, panel data, ARIMA**: use **statsmodels** (11,702★, BSD-3-Clause, pushed 2026-10-22). Its formula API and `.summary()` output are the closest thing Python has to R's `lm()`.
- **Distributions, bootstrap, permutation tests, and everything primitives-level**: use **SciPy** (15,142★, BSD-3-Clause, pushed 2026-10-21). 90% of the time it is already installed; it is the substrate the other two build on.
- **If you can only install one**: SciPy for general engineering work, statsmodels for anything that smells like econometrics, Pingouin if you write papers.

## Comparison table (GitHub and PyPI data, 2026-10-23)

| Dimension | SciPy | statsmodels | Pingouin |
|---|---|---|---|
| GitHub stars | 15,142 | 11,702 | 1,937 |
| Last commit | 2026-10-21 | 2026-10-22 | 2026-10-17 |
| License | BSD-3-Clause | BSD-3-Clause | **GPL-3.0** |
| Install | `pip install scipy` | `pip install statsmodels` | `pip install pingouin` |
| Primary API | Functions: `ttest_ind`, `chi2_contingency`, `bootstrap` | Objects: `OLS`, `MixedLM`, `ARIMA` with `.fit()` | Functions returning DataFrames |
| Regression | Basic `linregress` only | Full: OLS, WLS, GLS, GLM, mixed, IV, panel | Not provided |
| ANOVA | One-way only (`f_oneway`) | Full factorial via formulas | One-way, two-way, mixed, repeated measures |
| Effect sizes | No | Partial (some models) | Yes — Cohen's d, η², ε², odds ratio |
| Multiple-comparison correction | No (use `statsmodels`) | Yes (`multipletests`) | Yes (`pairwise_tests` built in) |
| Bayes factor | No | No | Yes (`pg.bayesfactor_ttest`) |
| Time series | No | Yes (ARIMA, VAR, state space) | No |
| Output format | Scalars / tuples | Rich text tables | DataFrame rows |
| Best for | Distributions, bootstrap, signal work | Modelling and inference | Reporting-ready test results |

## Decision matrix: match the library to the question

| Your question | Use | Why |
|---|---|---|
| "Is group A different from group B?" | Pingouin | Returns test + CI + effect size + power together |
| "Which of my 12 subgroups actually differ?" | Pingouin | `pairwise_tests()` applies Holm/Bonferroni automatically |
| "How does price respond to 6 covariates?" | statsmodels | `smf.ols()` gives coefficients, std errors, R², diagnostics |
| "My data has repeated measures per patient" | statsmodels | `MixedLM` or Pingouin's `mixed_anova` |
| "I need a chi-square p-value in a script" | SciPy | `chi2_contingency` — zero ceremony |
| "Bootstrap a confidence interval for a custom statistic" | SciPy | `scipy.stats.bootstrap` |
| "Forecast the next 12 months" | statsmodels | `ARIMA` / `SARIMAX` with prediction intervals |
| "Report a Bayes factor instead of a p-value" | Pingouin | `pg.bayesfactor_ttest` |
| "Fit a logistic regression" | statsmodels | `smf.logit` or `Logit` |
| "Permutation test on 40 samples" | SciPy | `permutation_test` with a custom statistic |

![statsmodels official logo](/img/screenshots/statsmodels-logo.jpg "statsmodels — statistical modelling and econometrics in Python")

## Pingouin — the reporting layer Python was missing

The standard SciPy workflow looks like this: call `ttest_ind`, get a statistic and a p-value, then manually compute Cohen's d, look up the power, and hope you remembered the pooled standard deviation formula. Pingouin collapses that into one call and returns a DataFrame you can paste into a paper.

```python
import numpy as np
import pingouin as pg

np.random.seed(123)
mean, cov, n = [4, 5], [(1, .6), (.6, 1)], 30
x, y = np.random.multivariate_normal(mean, cov, n).T

print(pg.ttest(x, y))
```

Real output from the project's own README:

```
       T    dof  alternative      p_val  CI95          cohen_d    power    BF10
 -3.401     58  two-sided        0.001  [-1.68 -0.43]     0.878    0.917  26.155
```

That single row contains the test statistic, degrees of freedom, the p-value, a 95% confidence interval on the mean difference, Cohen's d, achieved power, and a Bayes factor. Rebuilding it from SciPy takes roughly 25 lines and three formulas you have to get right.

The same design carries into ANOVA and correlation work:

```python
df = pg.read_dataset('mixed_anova')
print(df.anova(dv='Scores', between='Group', detailed=True))

data = pg.read_dataset('mediation')
print(data.pairwise_corr(columns=['X', 'M', 'Y'], covar=['Mbin']))
```

`pairwise_corr` returns uncorrected p-values *and* Holm-corrected p-values side by side, which is exactly what a reviewer asks for after the first submission.

**Where Pingouin stops:** it does not fit regression models, does not do time series, and has no mixed-effects engine. It is a statistics *test and reporting* library, not a modelling library.

**The license is the real decision point.** Pingouin is **GPL-3.0**, while SciPy and statsmodels are BSD-3-Clause. If you import Pingouin into a distributed commercial product, you inherit copyleft obligations that a permissive license would not impose. Internal analysis, research, and notebooks are fine. Shipping it inside a closed-source SaaS backend deserves a conversation with legal — or a reimplementation of the six formulas you actually use.

## statsmodels — the modelling workhorse

statsmodels is where you go when the question is "how much", not "different or not". It provides the formula interface, the diagnostics, and the model families that applied econometrics and social science depend on.

```python
import pandas as pd
import statsmodels.formula.api as smf

df = pd.read_csv("sales.csv")
model = smf.ols("revenue ~ ad_spend + season + C(region)", data=df).fit()
print(model.summary())

# Robust standard errors — the default in practice for heteroskedastic data
print(model.get_robustcov_results(cov_type="HC3").summary())
```

`summary()` gives coefficients, standard errors, t-values, p-values, confidence intervals, R², adjusted R², F-statistic, AIC/BIC, and residual diagnostics in one printable block. For repeated measurements, the mixed-effects interface handles random intercepts and slopes:

```python
import statsmodels.formula.api as smf

mixed = smf.mixedlm("score ~ treatment + week", data=df, groups=df["patient_id"]).fit()
print(mixed.summary())
```

For multiple-comparison correction — the thing SciPy deliberately does not provide — statsmodels ships the canonical implementation:

```python
from statsmodels.stats.multitest import multipletests

rejected, p_corrected, _, _ = multipletests(p_values, alpha=0.05, method="fdr_bh")
```

Practical notes from running this in production:

- **`summary()` is not a diagnostic.** Always inspect residuals; a high R² with structured residuals means the model is wrong, not good.
- **Convergence warnings are real.** `MixedLM` and `Logit` emit `ConvergenceWarning` when the optimiser gives up. Silencing it with `warnings.filterwarnings("ignore")` is how people ship broken models.
- **Categorical handling is implicit and surprising.** `C(region)` picks a reference level alphabetically unless you pass `C(region, Treatment(reference="EU"))`. Silent reference changes make coefficient tables incomparable between runs.
- **Version drift matters.** statsmodels has been changing default covariance handling and result-object attributes across minor releases; pin your version in `requirements.txt` if you publish numbers.

## SciPy — the substrate you already have

SciPy is not really a statistics *workflow* library; it is a numerical library that happens to contain `scipy.stats`. But it is also the one dependency you almost certainly already have, and for a large class of tasks it is the correct, lowest-friction answer.

```python
from scipy import stats
import numpy as np

# Two-sample t-test (Welch by default is what you usually want)
res = stats.ttest_ind(group_a, group_b, equal_var=False)
print(res.statistic, res.pvalue)

# Non-parametric alternative
print(stats.mannwhitneyu(group_a, group_b, alternative="two-sided"))

# Bootstrap a confidence interval for a custom statistic
def iqr(x, axis=-1):
    return np.percentile(x, 75, axis=axis) - np.percentile(x, 25, axis=axis)

ci = stats.bootstrap((sample,), iqr, confidence_level=0.95, n_resamples=9999)
print(ci.confidence_interval)
```

Two things SciPy does better than either competitor:

1. **Distributions.** If you need `gamma.ppf`, `lognorm.fit`, or a truncated normal sampler, this is the implementation everyone else wraps.
2. **Modern resampling.** `bootstrap` and `permutation_test` (both vectorised, both with proper confidence-interval methods) replaced a generation of hand-written loops.

Two things it deliberately does not do: **no effect sizes and no multiple-comparison correction.** You can bolt them on — statsmodels' `multipletests` is the standard choice — but if you find yourself writing that glue repeatedly, you have outgrown raw SciPy.

## Why this matters for reproducible analysis

The three libraries differ in what they make *easy*, and that shapes what your analysis actually contains. A SciPy-only script tends to report p-values without effect sizes, because effect sizes take extra code. A Pingouin-based analysis reports them by default, because they arrive for free. A statsmodels-based analysis tends to include model diagnostics, because `summary()` forces you to look at them.

That is a workflow argument, not a benchmarking one — and it is the reason the "which is faster" question is mostly irrelevant here. All three call into the same BLAS/LAPACK stack for the heavy lifting; differences in wall-clock time only appear at sample sizes where you should be thinking about out-of-core processing instead. For data preparation before any of this, see our [CSV processing comparison](../2026-06-17-csv-processing-csvkit-xsv-miller/), and for plotting the results our [Python visualisation roundup](../2026-08-18-matplotlib-vs-plotly-vs-bokeh-python-visualization-comparison/) covers the rendering side. If your statistics feed a service that validates incoming data, the [Python validation library comparison](../2026-07-26-python-validation-libraries-pydantic-cerberus-jsonschema/) covers schema enforcement.

## Pitfalls that produce wrong numbers

1. **Using `equal_var=True` (Student's t-test) on unequal-variance data.** SciPy's default is Student's; Pingouin's `pg.ttest` defaults to Welch. If group sizes differ, Welch is the safer default — set it explicitly and write down why.
2. **Reporting p-values without effect sizes.** With n=50,000 everything is "significant". Cohen's d, η² or an odds ratio tells the reader whether the effect matters.
3. **Forgetting the correction until the reviewer asks.** Run `multipletests(..., method="fdr_bh")` or Pingouin's `pairwise_tests(correction="holm")` from the start; retrofitting corrections changes your conclusions.
4. **Importing Pingouin into a closed-source product.** GPL-3.0 is copyleft. Internal use is fine; distribution is a legal question, not a technical one.
5. **Trusting `summary()` as validation.** Check residual plots, VIF for collinearity, and influence measures (`model.get_influence()`).
6. **Mixing library conventions.** Pingouin returns DataFrames, SciPy returns result objects, statsmodels returns model objects. Wrapping them in a single helper module early prevents the "which p-value column is this" bug.
7. **Ignoring missing-data behaviour.** SciPy's tests drop NaN silently in some paths and return NaN in others; statsmodels' formula API drops incomplete rows by default. Count your rows before and after, every time.

## FAQ

**Is Pingouin a replacement for statsmodels?**
No. Pingouin covers hypothesis tests and reporting (t-tests, ANOVA, correlations, effect sizes, power, Bayes factors). statsmodels covers modelling (regression, mixed effects, GLM, time series). A typical research pipeline uses Pingouin for the test table and statsmodels for the model.

**Is SciPy enough on its own?**
For distributions, bootstrap, permutation tests, and simple comparisons, yes. It has no effect sizes, no multiple-comparison correction, and only basic linear regression, so most analyses add either statsmodels or Pingouin on top.

**Which library should I use for ANOVA with repeated measures?**
Pingouin's `mixed_anova` handles one-way and two-way repeated-measures designs and returns effect sizes; statsmodels covers the same ground through `AnovaRM` and mixed-effects models. Pingouin's output is closer to publication format.

**Can I use these libraries commercially?**
SciPy and statsmodels are BSD-3-Clause — permissive, attribution only. Pingouin is GPL-3.0, which imposes copyleft obligations if you distribute software that imports it. Internal analytics are unaffected.

**Do I need to pin versions for reproducible results?**
Yes. All three evolve defaults between minor releases (covariance estimators, correction methods, result attributes). Record exact versions alongside your reported statistics, or your numbers may not reproduce six months later.

**What about R?**
If your team already lives in R, the tidyverse plus `emmeans` covers this ground with better defaults. The Python case here is about teams whose data pipeline is already Python and who do not want a second runtime in production.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "statsmodels vs Pingouin vs SciPy in 2026: Which Python Statistics Library Should You Actually Use?",
  "description": "Practical comparison of statsmodels, Pingouin and SciPy.stats for Python statistical analysis in 2026: regression, ANOVA, effect sizes, multiple comparisons, licensing and reproducible reporting.",
  "datePublished": "2026-10-23",
  "dateModified": "2026-10-23",
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
