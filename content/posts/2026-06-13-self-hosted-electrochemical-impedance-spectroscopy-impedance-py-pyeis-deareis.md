---
title: "Self-Hosted Electrochemical Impedance Spectroscopy: impedance.py vs PyEIS vs DearEIS vs AutoEIS"
date: "2026-06-13"
tags: ["electrochemistry", "impedance-spectroscopy", "scientific-computing", "python", "battery-research", "materials-science"]
draft: false
---

## Introduction

Electrochemical Impedance Spectroscopy (EIS) is the workhorse technique for characterizing batteries, fuel cells, corrosion processes, and biosensors. By applying a small AC perturbation and measuring the frequency-dependent impedance response, EIS reveals charge transfer kinetics, diffusion coefficients, and interfacial properties that DC methods cannot access.

Historically, EIS analysis meant expensive commercial software tied to specific potentiostat vendors. The open-source ecosystem has changed this completely — Python libraries now offer equivalent circuit fitting, distribution of relaxation times (DRT) analysis, Bayesian uncertainty quantification, and automated model selection, all deployable on lab servers for multi-user access.

This guide compares four leading open-source EIS analysis platforms: **impedance.py**, **PyEIS**, **DearEIS**, and **AutoEIS**.

## Tool Overview

| Tool | Language | Stars | Approach | Best For |
|------|----------|-------|----------|----------|
| impedance.py | Python | 282+ | Circuit fitting + DRT | Full-spectrum EIS analysis |
| PyEIS | Python | 220+ | Simulation + equivalent circuits | Teaching and method development |
| DearEIS | Python | 109+ | GUI + Bayesian fitting | Interactive exploration |
| AutoEIS | Python | 70+ | Automated model selection | High-throughput screening |

### impedance.py

impedance.py is the most comprehensive open-source EIS library. It provides Nyquist and Bode plotting, equivalent circuit fitting with customizable circuit elements, validation against Kramers-Kronig relations, and distribution of relaxation times (DRT) analysis. The library is designed for scriptable, reproducible workflows and integrates naturally with Jupyter notebooks.

Key capabilities:
- Equivalent circuit fitting with 20+ built-in circuit elements
- Kramers-Kronig validation (linear and measurement-model based)
- Distribution of Relaxation Times (DRT) via Tikhonov regularization
- Custom circuit definition via element composition
- Batch processing of multiple EIS spectra
- Publication-quality Nyquist and Bode plots

### PyEIS

PyEIS takes a simulation-first approach. Before fitting real data, you can simulate impedance spectra from any equivalent circuit and explore how parameter changes affect the Nyquist and Bode plots. This makes it particularly valuable for teaching EIS fundamentals and for method development when designing new experiments.

Key capabilities:
- Impedance simulation from arbitrary equivalent circuits
- Built-in circuit library (Randle's, Warburg variants, CPE models)
- Non-linear least squares fitting
- Confidence interval estimation for fitted parameters
- Interactive parameter exploration via widgets

### DearEIS

DearEIS provides a full graphical user interface built on Dear PyGui, making EIS analysis accessible without writing code. Behind the GUI, it uses advanced Bayesian inference for parameter estimation — providing not just best-fit values but full posterior probability distributions. This is especially valuable when equivalent circuit models have correlated parameters, where traditional least-squares fitting can converge to local minima.

Key capabilities:
- Interactive GUI for point-and-click EIS analysis
- Bayesian parameter estimation with Markov Chain Monte Carlo
- Full posterior distributions for fitted parameters
- Visual comparison of multiple equivalent circuit models
- Export to publication-ready figures

### AutoEIS

AutoEIS addresses the bottleneck in high-throughput EIS workflows: selecting the right equivalent circuit model. Instead of requiring the user to specify a circuit topology, AutoEIS automatically tests multiple candidate circuits, scores them by goodness-of-fit and complexity penalty, and returns the optimal model. For battery screening campaigns with hundreds of cells, this eliminates the most time-consuming manual step.

Key capabilities:
- Automated equivalent circuit model selection
- Multi-criteria model scoring (AIC, BIC, chi-squared)
- Built-in library of common battery and fuel cell circuits
- Batch processing of large datasets
- Integration with pandas DataFrames for results management

## Installation and Setup

All tools install via pip and can be deployed on a shared analysis server:

```bash
# Create isolated environment
python3 -m venv /opt/eis-env
source /opt/eis-env/bin/activate

# Install core libraries
pip install impedance PyEIS DearEIS auto-eis

# For server deployment with JupyterHub
pip install jupyterhub jupyterlab numpy scipy matplotlib pandas
```

Docker Compose for a lab EIS analysis server:

```yaml
version: "3.8"
services:
  eis-jupyter:
    image: jupyter/scipy-notebook:latest
    ports:
      - "8888:8888"
    volumes:
      - /data/eis-experiments:/home/jovyan/data
    environment:
      - JUPYTER_ENABLE_LAB=yes
    command: |
      start-notebook.sh --NotebookApp.token='' --NotebookApp.password=''
    # Install EIS packages on startup
    # pip install impedance PyEIS DearEIS auto-eis
```

## Comparison Table: Feature Matrix

| Feature | impedance.py | PyEIS | DearEIS | AutoEIS |
|---------|-------------|-------|---------|---------|
| Equivalent circuit fitting | Yes (20+ elements) | Yes (NLLS) | Yes (Bayesian) | Yes (automated) |
| Kramers-Kronig validation | Yes (linear + measurement) | No | No | Planned |
| DRT analysis | Yes (Tikhonov) | No | No | No |
| Circuit simulation | Via fitting | Native | Via fitting | No |
| GUI | No | No | Yes (Dear PyGui) | No |
| Bayesian inference | No | No | Yes (MCMC) | No |
| Automated model selection | No | No | No | Yes |
| Batch processing | Yes | Limited | Yes | Yes |
| Custom circuit elements | Yes | Yes | Via GUI | No |
| Publication plots | Yes | Basic | Yes | Via matplotlib |

For related reading: For complementary lab instrumentation, see our [electronics lab software comparison](../2026-06-09-self-hosted-electronics-lab-software-sigrok-scopy-eez-studio/). If your research involves sensor data, our [environmental sensor data platforms guide](../2026-06-12-self-hosted-environmental-sensor-data-platforms-guide/) covers related acquisition pipelines. For signal processing workflows, our [SDR and signal processing guide](../2026-06-07-self-hosted-signal-processing-sdr-gnuradio-liquid-dsp-soapysdr/) covers complementary analysis techniques.

## Why Self-Host Your EIS Analysis?

Vendor lock-in is the primary pain point in EIS analysis. Gamry, BioLogic, Solartron, and Metrohm each bundle proprietary analysis software that reads only their proprietary data formats. If your lab switches potentiostat vendors — or collaborates with a lab using different hardware — you lose access to years of analyzed data. Open-source EIS tools read multiple vendor formats (`.z`, `.dfr`, `.mpt`, `.dta`) and store results in open formats, future-proofing your data.

Computational reproducibility is the second major advantage. When a paper reports "the charge transfer resistance is 47.2 Ω," but doesn't specify which equivalent circuit was used, which weighting scheme, and what initial parameter guesses — the result is irreproducible. Scripted analysis with impedance.py or PyEIS captures every parameter choice in version-controlled code, which can be archived alongside the publication. Reviewers and future researchers can re-run the exact analysis.

For high-throughput labs — battery testing facilities that screen 500+ cells per month — AutoEIS's automated model selection is transformative. Instead of an electrochemist spending 10-15 minutes fitting each spectrum manually, AutoEIS processes all 500 spectra in a batch job, delivering a ranked list of the best-fit models for each cell. This alone can save 80+ hours per month for a busy battery lab.

## Choosing the Right Tool

### For Routine Battery Characterization
impedance.py is the go-to choice. Its equivalent circuit fitting handles the standard Randles circuit and variants (with Warburg, CPE, and Gerischer elements) that cover 90% of battery EIS spectra. The Kramers-Kronig validation is essential for checking data quality before fitting — impedance data that fails KK validation should not be fitted at all because it violates causality or linearity.

### For Method Development and Teaching
PyEIS's simulation capabilities are unmatched for understanding EIS. New students can simulate a Randles circuit, vary the charge transfer resistance, and instantly see how the Nyquist semicircle changes diameter. This interactive exploration builds intuition that staring at equations cannot. For designing new experiments, PyEIS lets you predict what your impedance spectrum should look like before running the potentiostat.

### For Non-Programmer Lab Members
DearEIS makes Bayesian EIS analysis accessible to anyone comfortable with a GUI. The interactive point-and-click interface requires no Python knowledge, yet produces publication-quality results with rigorous uncertainty quantification. Core facilities with rotating users particularly benefit — training time drops from weeks to hours.

### For High-Throughput Screening
AutoEIS is designed for scale. Feed it a directory of impedance spectra, and it returns a spreadsheet of optimal circuit models with fit quality metrics. For battery startups screening electrolyte formulations or electrode materials, AutoEIS eliminates the analysis bottleneck without requiring an electrochemist's time for each cell.

## Equivalent Circuit Modeling: Common Pitfalls

**Avoid overfitting.** A circuit with 12 parameters will always fit better than one with 3 — but the extra parameters may model noise, not physics. Use AutoEIS's AIC/BIC scoring to penalize model complexity, or DearEIS's Bayesian approach which naturally favors simpler models through the prior distribution. A good rule of thumb: if adding a circuit element doesn't reduce chi-squared by at least 30%, it's probably not justified.

**Always validate with Kramers-Kronig.** K-K relations are not optional — they're a mathematical requirement for any valid impedance spectrum. If your data fails K-K, it violates causality, linearity, or stability. Common causes: non-stationary systems (battery changing state during measurement), too-large AC amplitude, or instrument artifacts at high frequencies. impedance.py's K-K validation should be the first step in every EIS workflow.

## FAQ

### Can I use these tools with my commercial potentiostat?
Yes. impedance.py reads `.z` (Gamry), `.dfr` (Solartron), `.mpt` (BioLogic), and generic CSV/TSV formats. PyEIS and DearEIS accept numpy arrays directly, so any potentiostat that exports to CSV works. For proprietary binary formats, impedance.py's `preprocessing` module provides conversion utilities. Check your instrument's export options — most modern potentiostats export to text-based formats natively.

### How does Bayesian fitting differ from least-squares?
Traditional least-squares fitting returns a single best-fit value for each parameter (e.g., "R_ct = 47.2 Ω"). Bayesian fitting via DearEIS returns a full probability distribution — you learn not just the most likely value but the uncertainty range (e.g., "R_ct = 47.2 ± 2.1 Ω, 95% credible interval [43.1, 51.5]"). This matters when circuit parameters are correlated: least-squares can report tight confidence intervals that are artificially narrow, while Bayesian methods correctly capture parameter covariance.

### What's DRT and when should I use it?
Distribution of Relaxation Times (DRT) transforms impedance data from the frequency domain into a distribution of time constants. Instead of assuming a specific equivalent circuit topology, DRT reveals how many physical processes are present and their characteristic time scales — without committing to a circuit model. Use DRT when you're unsure which circuit model to fit, or when standard circuits can't reproduce your data. impedance.py implements DRT via Tikhonov regularization, and the resulting peaks directly suggest which circuit elements to include.

### Can I deploy these as a web application?
Yes. While DearEIS provides a desktop GUI, you can build a web-based EIS analysis portal using impedance.py as the backend with Streamlit, Dash, or FastAPI. A typical setup uses impedance.py for computation and Plotly for interactive visualization. This enables remote access — researchers can upload impedance data from home and get fitted results without VPN'ing into the lab.

### How do I handle very large datasets (1000+ spectra)?
For high-throughput workflows, use impedance.py with AutoEIS in batch mode. Load all spectra into a pandas DataFrame, define a processing function, and use `DataFrame.apply()` or multiprocessing to parallelize. A 64-core lab server can process 1000 spectra with equivalent circuit fitting in under 5 minutes. For DRT analysis, which is more computationally intensive, consider preprocessing spectra with AutoEIS first to eliminate obviously bad data, then run DRT only on the remaining high-quality subset.

### Are these tools suitable for electrochemical biosensor data?
Absolutely. EIS is a primary technique for label-free biosensing (detecting antibody-antigen binding, DNA hybridization, or cell adhesion by impedance changes). impedance.py's equivalent circuit fitting handles the constant phase element (CPE) models common in biosensor interfaces, and the Kramers-Kronig validation helps distinguish real binding events from electrode degradation artifacts. For biosensor arrays with dozens of electrodes, AutoEIS's batch processing is essential.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Electrochemical Impedance Spectroscopy: impedance.py vs PyEIS vs DearEIS vs AutoEIS",
  "description": "Compare open-source EIS analysis tools: impedance.py for full-spectrum fitting and DRT, PyEIS for simulation, DearEIS for Bayesian GUI analysis, and AutoEIS for automated model selection. Docker deployment included.",
  "datePublished": "2026-06-13",
  "dateModified": "2026-06-13",
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

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
