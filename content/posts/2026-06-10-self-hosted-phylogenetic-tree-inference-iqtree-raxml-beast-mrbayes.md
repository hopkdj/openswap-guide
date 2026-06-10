---
title: "Self-Hosted Phylogenetic Tree Inference: IQ-TREE 2 vs RAxML-NG vs BEAST 2 vs MrBayes"
date: "2026-06-10"
tags: ["phylogenetics", "bioinformatics", "evolutionary-biology", "bayesian-inference", "maximum-likelihood", "molecular-evolution"]
draft: false
---

Phylogenetic trees — the branching diagrams depicting evolutionary relationships among species, genes, or populations — are the lingua franca of evolutionary biology. From tracking viral outbreaks to resolving deep branches of the tree of life, phylogenetics underpins our understanding of how life diversified over 4 billion years.

Modern phylogenetic inference splits into two philosophical camps: **maximum likelihood** (find the single best tree under an evolutionary model) and **Bayesian inference** (sample from the posterior distribution of trees). Four open-source tools — **IQ-TREE 2**, **RAxML-NG**, **BEAST 2**, and **MrBayes** — represent the state of the art, each with distinct strengths optimized for different research questions.

## The Two Paradigms of Phylogenetic Inference

### Maximum Likelihood (ML)

ML methods search tree space for the topology and branch lengths that maximize the probability of observing the sequence alignment under a specified substitution model (e.g., GTR+G+I). ML is computationally efficient, scales to thousands of taxa, and produces a single best tree with bootstrap support values.

**IQ-TREE 2** and **RAxML-NG** are the two dominant ML implementations, each with unique optimizations.

### Bayesian Inference (BI)

BI methods sample from the posterior probability distribution of trees given the data and prior beliefs. Rather than producing one "best" tree, they generate a set of credible trees with posterior probability support values. BI is more computationally intensive but provides richer uncertainty quantification.

**BEAST 2** and **MrBayes** are the leading Bayesian packages, differentiated by their focus on time-calibrated phylogenies and model flexibility respectively.

## Tool-by-Tool Analysis

### IQ-TREE 2: The Swiss Army Knife of ML Phylogenetics

IQ-TREE 2, developed at the University of Vienna, has rapidly become the most popular ML phylogenetics tool with over 330 GitHub stars. Its killer feature is **ModelFinder** — automatic model selection that tests 286 substitution models in seconds, choosing the best-fit model by BIC before tree inference begins.

**Key innovations:**
- Ultrafast bootstrap approximation (UFBoot) — 10-40x faster than standard bootstrap with comparable accuracy
- Single branch tests (aLRT, SH-aLRT) for rapid branch support assessment
- Partitioned analyses allowing different genes to evolve under different models
- Built-in tree topology tests (AU test, KH test, SH test)
- Native support for phylogenomic datasets with hundreds of loci

**Installation:**
```bash
# Conda (easiest)
conda create -n iqtree-env -c bioconda iqtree
conda activate iqtree-env

# Download binary (Linux)
wget https://github.com/iqtree/iqtree2/releases/download/v2.3.6/iqtree-2.3.6-Linux-intel.tar.gz
tar -xzf iqtree-2.3.6-Linux-intel.tar.gz
export PATH=$PATH:$(pwd)/iqtree-2.3.6-Linux-intel/bin

# Docker
docker pull quay.io/biocontainers/iqtree:2.3.6--h5b5514e_0
```

**Example command:**
```bash
# Auto model selection + ML tree + ultrafast bootstrap
iqtree2 -s alignment.phy -m MFP -B 1000 -T 16

# Partitioned analysis
iqtree2 -s concatenated.phy -p partition.nex -m MFP+MERGE -B 1000 -T 32
```

### RAxML-NG: Battle-Tested Performance at Scale

RAxML-NG (Next Generation), maintained by Alexey Kozlov at the Heidelberg Institute for Theoretical Studies, represents a complete rewrite of the classic RAxML codebase. With over 460 GitHub stars, it excels at large-scale phylogenomic analyses with hundreds to thousands of taxa.

**Differentiating features:**
- Superior parallelization — near-linear scaling to 64+ cores
- Efficient checkpointing — resume interrupted analyses from exact stopping point
- Flexible partition models with automatic merging of similar partitions
- Robust handling of alignment gaps and missing data
- Tree inference from a starting parsimony tree, avoiding the need for separate starting tree generation

**Installation:**
```bash
# Conda
conda create -n raxml-env -c bioconda raxml-ng
conda activate raxml-env

# Source build
git clone --recursive https://github.com/amkozlov/raxml-ng.git
cd raxml-ng && mkdir build && cd build
cmake .. && make -j16
```

**Example command:**
```bash
# Standard ML search with bootstrapping
raxml-ng --msa alignment.phy --model GTR+G --threads 32

# All-in-one (model test + ML search + bootstrapping)
raxml-ng --all --msa alignment.phy --model GTR+G --threads 32 --bs-trees 1000
```

### BEAST 2: Time-Calibrated Bayesian Phylogenetics

BEAST 2 (Bayesian Evolutionary Analysis Sampling Trees), from the University of Auckland, uniquely integrates temporal information — fossil calibrations, tip dates, and sampling times — directly into phylogenetic inference. With over 240 GitHub stars, it's the premier tool for estimating divergence times from molecular data.

**Distinctive capabilities:**
- Simultaneous estimation of tree topology, branch lengths, substitution parameters, and divergence times
- Flexible clock models (strict, uncorrelated lognormal, random local)
- Coalescent-based phylodynamic models for viral outbreak reconstruction
- Structured coalescent for phylogeography (tracing spatial spread)
- Extensive plugin system (BEAST 2 packages) covering discrete trait evolution, species tree inference, and more
- Beautiful interactive visualization via BEAUti and Tracer

**Installation:**
```bash
# Download from official site
wget https://github.com/CompEvol/beast2/releases/download/v2.7.7/BEAST.v2.7.7.Linux.tgz
tar -xzf BEAST.v2.7.7.Linux.tgz
cd beast

# Install common packages
./bin/packagemanager -add BEASTLabs
./bin/packagemanager -add SNAPP
./bin/packagemanager -add bModelTest
```

**Example XML (generated via BEAUti GUI):**
BEAST 2 uses an XML input format generated by its companion GUI, BEAUti, which specifies the sequence alignment, substitution model, clock model, tree prior, and MCMC settings. For server deployments without a GUI, XML files can be generated locally and transferred.

### MrBayes: Flexible Model Specification

MrBayes, maintained by the Swedish National Bioinformatics Infrastructure, is the original Bayesian phylogenetics powerhouse with nearly 270 GitHub stars. Its strength lies in its unparalleled model flexibility — you can specify different substitution models, rate partitions, and constraints with a simple command-block syntax.

**Key strengths:**
- Mixed models — combine different substitution models across data partitions
- Flexible prior specification for parameters and topologies
- Posterior predictive simulation for model adequacy testing
- Stepping-stone sampling for rigorous model comparison via marginal likelihood
- Robust handling of ambiguous characters and alignment uncertainty

**Installation:**
```bash
# Conda
conda create -n mrbayes-env -c bioconda mrbayes
conda activate mrbayes-env

# Docker
docker pull quay.io/biocontainers/mrbayes:3.2.7--h4ac6f70_0
```

**Example MrBayes block (in NEXUS file):**
```
begin mrbayes;
  set autoclose=yes nowarn=yes;
  lset nst=6 rates=invgamma;
  mcmc ngen=10000000 samplefreq=1000 nchains=4;
  sumt burnin=2500;
end;
```

## Comprehensive Comparison Table

| Feature | IQ-TREE 2 | RAxML-NG | BEAST 2 | MrBayes |
|---------|-----------|----------|---------|---------|
| **Inference Method** | Maximum Likelihood | Maximum Likelihood | Bayesian MCMC | Bayesian MCMC |
| **Output** | Single best tree + support | Single best tree + support | Posterior tree sample | Posterior tree sample |
| **Support Values** | UFBoot, aLRT, SH-aLRT | Standard bootstrap | Posterior probability | Posterior probability |
| **Model Selection** | ModelFinder (automatic) | Manual | bModelTest (plugin) | Manual + stepping-stone |
| **Divergence Time** | No | No | Yes (core feature) | Limited (node calibrations) |
| **Parallelization** | Good (16-32 cores) | Excellent (64+ cores) | Poor (single chain) | Good (multiple chains) |
| **Checkpoint/Restart** | Yes | Yes (exact resume) | Yes | Yes |
| **Partitioned Models** | Yes, with automatic merging | Yes, with automatic merging | Via plugins | Yes, flexible specification |
| **GUI** | No | No | BEAUti + Tracer | No |
| **Learning Curve** | Low | Moderate | High | Moderate-High |
| **Viral Phylodynamics** | No | No | Yes (coalescent models) | No |
| **Phylogeography** | No | No | Yes (structured coalescent) | No |
| **Scalability** | Hundreds of taxa | Thousands of taxa | 50-200 taxa (practical) | 100-500 taxa |
| **GitHub Stars** | 331 | 466 | 245 | 269 |
| **License** | GPL-2.0 | AGPL-3.0 | LGPL-2.1 | GPL-3.0 |

## Self-Hosted Deployment for Phylogenetics Labs

A dedicated phylogenetics server typically pairs ML and Bayesian tools on the same machine, choosing between them based on the specific research question:

```yaml
# docker-compose.yml for phylogenetics compute server
version: '3.8'
services:
  iqtree:
    image: quay.io/biocontainers/iqtree:2.3.6--h5b5514e_0
    volumes:
      - ./data:/data
      - ./results:/results
    working_dir: /data
    entrypoint: ["iqtree2"]

  raxml-ng:
    image: quay.io/biocontainers/raxml-ng:1.2.2--h4ac6f70_0
    volumes:
      - ./data:/data
      - ./results:/results
    working_dir: /data
    entrypoint: ["raxml-ng"]

  mrbayes:
    image: quay.io/biocontainers/mrbayes:3.2.7--h4ac6f70_0
    volumes:
      - ./data:/data
      - ./results:/results
    working_dir: /data
    stdin_open: true
    tty: true

  # Supplementary: visualization server
  figtree-server:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./results:/usr/share/nginx/html/results
```

For compute-intensive Bayesian analyses (BEAST 2, MrBayes) that may run for days or weeks, integration with [HPC workload managers](../2026-05-02-slurm-vs-openpbs-vs-htcondor-self-hosted-hpc-workload-managers-guide/) is essential. A Slurm submission script can launch multiple independent MCMC chains in parallel:

```bash
#!/bin/bash
#SBATCH --job-name=beast_tree
#SBATCH --time=168:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --array=1-4

cd /data/beast_run_${SLURM_ARRAY_TASK_ID}
beast -seed ${RANDOM} -threads 8 analysis.xml
```

## Why Self-Host Phylogenetic Inference Pipelines?

**Computational demands require dedicated hardware.** Phylogenetic inference at scale is computationally intensive — a Bayesian analysis of 200 taxa under a complex partitioned model with 10 million MCMC generations can consume 1,000+ CPU-hours. Cloud-based solutions charge premium rates for sustained compute, making a dedicated on-premises server with 32+ cores dramatically cheaper for any lab running more than one analysis per month. The amortized cost favors self-hosting within 6-12 months for active phylogenetics groups.

**Model control and method transparency.** The choice of substitution model (GTR, HKY, WAG, LG) and rate heterogeneity parameters directly affects phylogenetic conclusions. Many cloud-hosted tools obscure model selection behind "smart defaults" that may be inappropriate for non-model organisms or rapidly evolving viral sequences. Self-hosting lets you explicitly specify models, examine likelihood scores at each step, and document the full analytical pipeline from raw alignment to final tree — essential for [reproducible research practices](../2026-06-10-self-hosted-reproducible-research-binderhub-renku-stencila-guide/).

**Integration with genomic data pipelines.** Phylogenetic trees are rarely the final output — they feed into downstream analyses including ancestral state reconstruction, gene family evolution, and comparative genomics. Self-hosted pipelines integrate naturally with [scientific data management systems](../2026-06-09-self-hosted-scientific-data-management-irods-rucio-datalad-guide/) that track provenance from raw sequencing reads through alignment to final tree. This is particularly important for collaborative projects where multiple labs contribute data.

**Custom model implementation.** Both BEAST 2 and MrBayes support user-defined substitution models and tree priors via scripting. For researchers studying organisms with unusual evolutionary dynamics — codon-position-specific rates in RNA viruses, strand-specific substitution bias in mitochondrial genomes, or heterotachy in deep phylogenetics — custom models are essential and only available through self-hosted deployments.

**Sensitive data handling.** Phylogenetic analyses of pathogens (viral outbreaks, antimicrobial resistance surveillance) often involve sequences from clinical samples with privacy implications. Self-hosting ensures that pathogen genomic data remains within institutional security boundaries, compliant with public health data governance requirements. For viral outbreak analysis, BEAST 2's phylodynamic models combined with self-hosted infrastructure have been used by major public health agencies to track transmission chains without exposing patient-associated sequence data to external services.

## Choosing the Right Tool for Your Research Question

| Research Question | Recommended Tool |
|-------------------|------------------|
| What is the most likely tree for this alignment? | IQ-TREE 2 (with ModelFinder + UFBoot) |
| I have 500+ taxa and need a tree fast | RAxML-NG (best parallelization) |
| When did these species diverge? | BEAST 2 (simultaneous divergence time estimation) |
| How did this virus spread geographically? | BEAST 2 (structured coalescent phylogeography) |
| I need to test whether my model fits the data | MrBayes (posterior predictive simulation) |
| I have mixed data types (morphology + DNA) | MrBayes (flexible mixed models) |
| Best for beginners | IQ-TREE 2 (automatic model selection, simple CLI) |

## FAQ

### Maximum likelihood or Bayesian — which is better?

Neither is categorically better — they answer different questions. ML produces a point estimate (best tree) with bootstrap support, suitable for hypothesis testing and exploratory analysis. Bayesian inference produces a posterior distribution, useful when quantifying uncertainty matters (divergence time estimation, ancestral state reconstruction). In practice, many researchers run both on the same dataset — ML for a quick best tree, Bayesian for rigorous uncertainty quantification and time calibration.

### How many bootstrap replicates do I need?

For ML analysis with IQ-TREE 2, 1,000 ultrafast bootstrap replicates are standard and computationally cheap. For RAxML-NG with standard bootstrapping, 100-500 replicates are common given the higher computational cost. Bayesian posterior probabilities from BEAST 2 or MrBayes do not require replicates — they are derived from the MCMC sample directly.

### Can I run BEAST 2 on a headless server?

Yes, but the primary interface (BEAUti) requires a GUI for setting up analyses. Workaround: generate the XML file on a local machine with BEAUti, then transfer to the server for headless execution. Alternatively, BEAST 2 XML can be written programmatically — several R packages (babette, beautier) provide programmatic interfaces for generating BEAST 2 input files.

### How do I know if my MCMC chain has converged?

Check ESS (Effective Sample Size) values > 200 for all parameters, and examine trace plots for mixing. Tracer (from the BEAST 2 ecosystem) is the standard tool for MCMC diagnostics. For MrBayes, the `.pstat` and `.tstat` output files contain convergence diagnostics. Run at least two independent chains and compare — their posterior probability estimates should agree within 5%.

### How long will my analysis take?

IQ-TREE 2 with UFBoot on 200 taxa: ~2-4 hours on 16 cores. RAxML-NG on 1,000 taxa: ~8-12 hours. BEAST 2 on 100 taxa with molecular clock: ~24-72 hours for 100 million generations. MrBayes on 200 taxa: ~48-168 hours for 10 million generations. All times scale with alignment length, model complexity, and number of taxa.

### Can I combine results from ML and Bayesian analyses?

Yes — and this is recommended. Present the ML tree (from IQ-TREE 2 or RAxML-NG) as your primary result with bootstrap support values, and the Bayesian consensus tree (from BEAST 2 or MrBayes) with posterior probabilities as a supplementary figure. Agreement between ML and Bayesian topologies strengthens confidence in evolutionary relationships; disagreement flags branches that deserve further investigation with additional data or alternative models.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Phylogenetic Tree Inference: IQ-TREE 2 vs RAxML-NG vs BEAST 2 vs MrBayes",
  "description": "Comprehensive comparison of four leading open-source phylogenetic tree inference tools — IQ-TREE 2 and RAxML-NG for maximum likelihood, BEAST 2 and MrBayes for Bayesian inference — covering installation, deployment, performance characteristics, and best practices for self-hosted evolutionary bioinformatics.",
  "datePublished": "2026-06-10",
  "dateModified": "2026-06-10",
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
