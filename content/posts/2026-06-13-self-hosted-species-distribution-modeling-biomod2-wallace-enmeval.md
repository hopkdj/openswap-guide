---
title: "Self-Hosted Species Distribution Modeling: biomod2 vs Wallace vs ENMeval"
date: "2026-06-13"
tags: ["ecology", "species-distribution", "biodiversity", "conservation", "r-language", "gis", "environmental-modeling", "scientific-computing"]
draft: false
---

## Introduction

Species Distribution Modeling (SDM) is a cornerstone of modern ecology and conservation biology. These models predict where species occur based on environmental conditions, helping researchers understand habitat suitability, forecast climate change impacts, and guide conservation planning. As biodiversity faces unprecedented threats, the ability to accurately model species distributions with self-hosted, reproducible tools has never been more critical.

The R statistical computing ecosystem dominates SDM research, offering three complementary platforms: **biomod2** for ensemble forecasting with multi-model consensus, **Wallace** for interactive, GUI-driven modeling with built-in reproducibility features, and **ENMeval** for rigorous model tuning through optimized complexity selection.

Each platform addresses different needs in the SDM workflow — from exploratory analysis to high-throughput ensemble modeling to publication-quality model optimization. This guide compares their approaches, deployment strategies, and practical applications.

## Platform Overview

| Feature | biomod2 | Wallace | ENMeval |
|---------|---------|---------|---------|
| **GitHub Stars** | 124+ | 143+ | 56+ |
| **Interface** | R package (CLI) | Shiny web application | R package (CLI) |
| **Model Types** | 10+ algorithms | 4 core algorithms | Maxent-focused |
| **Ensemble Methods** | Yes (built-in) | No | No |
| **Reproducibility** | Script-based | R Markdown export | Script-based |
| **Model Evaluation** | TSS, ROC, KAPPA | AUC, CBI, Omission | AICc, AUC, OR |
| **Spatial Thinning** | Manual | Built-in | Manual |
| **R Version** | ≥ 4.0 | ≥ 4.1 | ≥ 4.0 |

**biomod2** is the veteran ensemble modeling platform. Maintained by Wilfried Thuiller's lab, it integrates over 10 modeling algorithms — including GLM, GAM, GBM, Random Forest, Maxent, and MARS — into a unified workflow. Its ensemble forecasting approach averages predictions across multiple algorithms, producing more robust projections than any single model. biomod2 is the tool of choice for large-scale biodiversity assessments and climate change impact studies.

**Wallace** takes a fundamentally different approach by wrapping the SDM workflow in an interactive Shiny web application. Developed by the CUNY-Hunter College biodiversity lab, Wallace guides users through the entire modeling process: data acquisition (GBIF integration), data cleaning, environmental data retrieval (WorldClim), model fitting, and evaluation. Every session generates an R Markdown script for full reproducibility. Wallace is ideal for teaching, exploratory analysis, and researchers new to SDM.

**ENMeval** specializes in one critical but often-overlooked aspect of SDM: model tuning. Maxent, the most widely used SDM algorithm, is sensitive to two key parameters — feature classes and regularization multipliers. Default settings can produce overfit models that perform poorly when transferred to new environments. ENMeval systematically tests combinations of these parameters, using information criteria (AICc) to select optimal complexity. It is essential for any publication-quality Maxent analysis.

## Deployment and Installation

### Installing biomod2

biomod2 requires R with several Bioconductor and CRAN dependencies:

```r
# Install R and system dependencies
# Ubuntu/Debian:
sudo apt-get install r-base r-base-dev libgdal-dev libproj-dev     libgeos-dev libudunits2-dev libgsl-dev

# In R console:
install.packages(c("devtools", "dismo", "raster", "sp", "rgdal",
    "randomForest", "gbm", "mgcv", "nnet", "earth", "mda",
    "rpart", "PresenceAbsence", "ggplot2"))

# Install biomod2 from GitHub
devtools::install_github("biomodhub/biomod2")

# Verify installation
library(biomod2)
```

Basic biomod2 workflow:

```r
library(biomod2)

# 1. Format data
myBiomodData <- BIOMOD_FormatingData(
    resp.var = mySpeciesData$presence,
    expl.var = myEnvStack,
    resp.name = "MySpecies",
    PA.nb.rep = 3,
    PA.nb.absences = 1000,
    PA.strategy = "random"
)

# 2. Define modeling options
myBiomodOptions <- BIOMOD_ModelingOptions()

# 3. Run individual models
myBiomodModelOut <- BIOMOD_Modeling(
    myBiomodData,
    models = c("GLM", "GAM", "GBM", "RF", "MAXENT", "MARS"),
    models.options = myBiomodOptions,
    NbRunEval = 5,
    DataSplit = 70,
    VarImport = 3,
    models.eval.meth = c("TSS", "ROC"),
    SaveObj = TRUE
)

# 4. Ensemble forecasting
myBiomodEM <- BIOMOD_EnsembleModeling(
    myBiomodModelOut,
    models.chosen = "all",
    em.by = "all",
    em.algo = c("EMmean", "EMca", "EMmedian"),
    eval.metric = c("TSS"),
    eval.metric.quality.threshold = 0.7,
    prob.mean = TRUE
)

# 5. Project to current and future climates
myBiomodProj <- BIOMOD_Projection(
    myBiomodModelOut,
    new.env = futureClimateStack,
    proj.name = "2050_RCP85",
    selected.models = "all",
    compress = TRUE,
    build.clamping.mask = TRUE
)
```

For high-throughput ensemble modeling, deploy biomod2 as a background job:

```bash
#!/bin/bash
# biomod2_batch.sh - Run ensemble SDM on multiple species
for species in species_list.txt; do
    Rscript run_biomod2.R $species &
done
wait
```

### Deploying Wallace as a Self-Hosted Web Application

Wallace's Shiny interface makes it uniquely suited for self-hosted deployment accessible via browser:

```r
# Install Wallace
install.packages("wallace")

# Install required dependencies
install.packages(c("shiny", "shinythemes", "shinyBS", "shinyjs",
    "leaflet", "leaflet.extras", "DT", "rintrojs", "spThin",
    "ENMeval", "dismo", "raster", "maptools", "rgdal"))

# Launch Wallace locally (port 8888)
library(wallace)
run_wallace(host = "0.0.0.0", port = 8888)
```

For production deployment, containerize Wallace with Docker:

```yaml
version: '3.8'
services:
  wallace:
    image: rocker/shiny:4.3.0
    ports:
      - "3838:3838"
    environment:
      SHINY_HOST: "0.0.0.0"
      SHINY_PORT: "3838"
    volumes:
      - ./wallace_app:/srv/shiny-server/wallace
      - ./wallace_data:/home/shiny/data
      - ./wallace_logs:/var/log/shiny-server
    restart: unless-stopped

  shiny-proxy:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - wallace
```

Wallace accesses GBIF and WorldClim APIs by default, but for air-gapped environments, download data locally:

```bash
# Download WorldClim bioclimatic variables (10 arc-minutes)
wget https://biogeo.ucdavis.edu/data/worldclim/v2.1/base/wc2.1_10m_bio.zip

# Download elevation data
wget https://biogeo.ucdavis.edu/data/worldclim/v2.1/base/wc2.1_10m_elev.zip

# Store in persistent volume for offline Wallace use
```

### ENMeval for Model Tuning

ENMeval integrates directly into R workflows:

```r
install.packages("ENMeval")
library(ENMeval)

# Set up tuning experiment
enmeval_results <- ENMevaluate(
    occs = occurrence_points,
    envs = environmental_stack,
    bg = background_points,
    algorithm = 'maxent.jar',
    tune.args = list(
        fc = c("L", "LQ", "H", "LQH", "LQHP"),
        rm = seq(1, 6, 0.5)
    ),
    partitions = 'block',
    partition.settings = list(aggregation.factor = c(4, 4)),
    parallel = TRUE,
    numCores = 8
)

# Select optimal model by AICc
optimal_model <- eval.results(enmeval_results)
print(optimal_model)

# Extract best parameters
best_fc <- optimal_model$fc[which.min(optimal_model$AICc)]
best_rm <- optimal_model$rm[which.min(optimal_model$AICc)]

# Run final Maxent with optimized parameters
final_model <- maxent(
    environmental_stack,
    occurrence_points,
    args = c(
        paste0("betamultiplier=", best_rm),
        paste0("features=", best_fc)
    )
)
```

Best practices for ENMeval include spatial block partitioning to avoid geographic overfitting and testing regularization multipliers from 1 to 6:

```r
# Spatial block partitioning prevents overfitting
block_results <- ENMevaluate(
    occs = occs,
    envs = envs,
    bg = bg,
    tune.args = list(fc = c("L", "LQ", "LQH", "LQHP"),
                     rm = 1:6),
    partitions = "block",
    parallel = TRUE,
    numCores = 4
)

# Compare models
evalplot.stats(e = block_results, stats = "AICc", color = "fc")
evalplot.stats(e = block_results, stats = "auc.val", color = "fc")
```

## Comparison of Methodologies

### Data Preparation

| Aspect | biomod2 | Wallace | ENMeval |
|--------|---------|---------|---------|
| Occurrence cleaning | Manual (dismo) | GUI + spThin | Manual |
| Background selection | Random, disk, user-defined | Min convex polygon | Random, user-defined |
| Environmental data | RasterStack input | WorldClim/SRTM download | RasterStack input |
| Spatial thinning | Manual | Built-in (spThin) | Manual |
| GBIF integration | Via rgbif | Built-in module | Via rgbif |

Wallace excels in data preparation, providing an integrated pipeline for occurrence data acquisition (GBIF search), cleaning (coordinate error detection, duplicate removal), and spatial thinning (minimum distance filtering). biomod2 and ENMeval require manual data preparation but offer more flexibility for custom data sources.

### Model Evaluation and Selection

biomod2's ensemble approach is its defining strength. After running 10+ algorithms with multiple cross-validation splits, users select the best-performing models and combine them. The consensus approach reduces single-model bias and provides uncertainty estimates through model-to-model variation.

ENMeval's contribution is systematic hyperparameter tuning. Many published Maxent models use default settings that produce overfit predictions — ENMeval's AICc-based selection identifies the right balance between model fit and complexity. For transferability (predicting to new time periods or regions), ENMeval offers sequential block partitioning that better reflects real-world extrapolation challenges.

Wallace provides a streamlined evaluation dashboard with real-time feedback on model performance. It calculates standard metrics (AUC, omission rate, Continuous Boyce Index) and displays them in interactive plots. The R Markdown export ensures that every modeling decision is documented.

## Performance and Hardware Requirements

SDM workloads are typically CPU-bound (not GPU-accelerated). For a typical modeling project involving 50 species, 5 climate scenarios, and 10 ensemble members per species:

| Configuration | biomod2 | Wallace | ENMeval |
|---------------|---------|---------|---------|
| **Small (4 cores, 16GB)** | 2-4 hours | Real-time | 1-2 hours |
| **Medium (16 cores, 32GB)** | 30-60 min | Real-time | 15-30 min |
| **Large (64 cores, 128GB)** | 10-20 min | Real-time | 5-10 min |
| **Disk Space** | 10-50 GB | 1-5 GB | 5-20 GB |

Parallel processing dramatically speeds up ensemble modeling:

```r
# biomod2 with parallel processing
library(doParallel)
registerDoParallel(cores = 16)
myBiomodModelOut <- BIOMOD_Modeling(
    myBiomodData,
    models = c("GLM", "GBM", "RF", "MAXENT", "MARS", "GAM"),
    NbRunEval = 5,
    DataSplit = 70,
    models.eval.meth = c("TSS", "ROC"),
    do.full.models = FALSE
)
```

## Why Self-Host Species Distribution Models?

Self-hosted SDM platforms provide reproducibility and transparency that cloud-based alternatives cannot match. Every modeling decision — from background point selection to regularization parameters — is documented in executable R scripts. This is critical for peer-reviewed research where reviewers may request model replication.

Data sovereignty matters in conservation. Species occurrence data may include locations of endangered species (red-listed by IUCN) that should not be publicly exposed due to poaching risks. Self-hosting keeps sensitive location data within institutional firewalls.

For related ecological and environmental modeling tools, see our [weather station and environmental monitoring guide](../2026-05-04-self-hosted-weather-station-software-weewx-meteobridge-weather34-guide/) and our [geospatial database comparison](../2026-05-20-self-hosted-geospatial-database-tile38-postgis-redis-guide/). For biodiversity data management, check our [research data management platforms](../2026-06-09-self-hosted-scientific-data-management-irods-rucio-datalad-guide/).

## Expand Your Analysis Pipeline

Beyond the core SDM workflow, consider integrating these complementary tools for a complete analytical pipeline. Post-modeling, spatial analysis libraries like `sf` and `terra` enable habitat fragmentation analysis and connectivity modeling. For visualizing results, `tmap` and `leaflet` produce publication-quality static and interactive maps directly from SDM outputs.

For projects spanning multiple species and scenarios, workflow managers like `targets` (R) or Snakemake ensure reproducible, cache-aware pipelines that only recompute changed steps. This is particularly valuable for climate change impact assessments that may involve hundreds of models across dozens of species.

Version control for geospatial data can be handled through tools like `datalad`, which extends Git for large scientific datasets. Combined with container technologies (Docker/Singularity) for environment reproducibility, a self-hosted SDM infrastructure achieves the gold standard of computational reproducibility.

## FAQ

### Can I use these tools without R programming experience?

Wallace is explicitly designed for users with limited R experience. Its Shiny GUI provides point-and-click access to the entire SDM workflow, and the generated R Markdown script allows gradual learning of the underlying code. biomod2 and ENMeval require reasonable R proficiency — expect to invest 1-2 weeks learning these packages if you're new to R.

### How do I handle large environmental datasets (100GB+)?

For massive environmental datasets, use `terra` package instead of `raster` — it provides C++-backed operations with memory-safe processing. Set up a processing pipeline that tiles the study area:

```r
library(terra)
env_stack <- rast("global_climate.tif")
tiles <- makeTiles(env_stack, c(1000, 1000))
for(tile in tiles) {
    tile_data <- rast(tile)
    # Process tile
}
```

For cloud-based workflows, use `gdalcubes` to process multidimensional raster data without loading everything into memory.

### Which algorithm should I use for my species data?

For species with < 30 occurrence records: Maxent or BIOCLIM. For 30-100 records: Maxent, GAM, or BRT. For >100 records: ensemble of multiple algorithms (RF + GBM + GLM + Maxent + MARS). biomod2's ensemble approach automatically handles this by weighting individual models based on evaluation metrics. Always run ENMeval before publishing Maxent-based SDMs — default Maxent settings overfit with small sample sizes.

### Can I transfer models across time periods or geographic regions?

Model transfer is the most challenging SDM application. For temporal transfer (climate change projections), ENMeval provides the `occs.train.z` and `occs.val.z` partitioning that separates training and testing by time. For spatial transfer, use `checkerboard` or `block` partitioning. Avoid `randomkfold` partitioning for transfer studies — it produces overly optimistic evaluation metrics. Always generate Multivariate Environmental Similarity Surface (MESS) maps to identify extrapolation areas:

```r
library(dismo)
mess_map <- mess(future_climate, reference_points)
```

### What's the difference between correlation and causation in SDM?

SDMs are correlative, not mechanistic. They identify environmental correlates of species presence but don't prove causation. A species may be absent from climatically suitable areas due to dispersal limitations, biotic interactions, or historical factors. To address this, combine SDMs with mechanistic models (like NicheMapR) or process-based models for stronger inference. Always report model uncertainty and avoid over-interpreting SDM results as definitive habitat maps.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Species Distribution Modeling: biomod2 vs Wallace vs ENMeval",
  "description": "Comprehensive comparison of three open-source species distribution modeling platforms: biomod2 (ensemble forecasting), Wallace (interactive Shiny application), and ENMeval (Maxent model tuning). Covers deployment, methodology comparison, hardware requirements, and reproducibility best practices for ecological modeling.",
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
      "url": "https://pistack.xyz/logo.png"
    }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
