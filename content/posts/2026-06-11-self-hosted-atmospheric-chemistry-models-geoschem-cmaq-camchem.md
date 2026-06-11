---
title: "Self-Hosted Atmospheric Chemistry Models: GEOS-Chem vs CMAQ vs CAM-Chem"
date: "2026-06-11"
tags: ["atmospheric-chemistry", "scientific-computing", "air-quality", "climate-modeling", "geos-chem", "cmaq", "cam-chem"]
draft: false
---

## Introduction

Atmospheric chemistry transport models are the computational backbone of air quality forecasting, climate change research, and environmental policy assessment. These models simulate the emission, transport, chemical transformation, and deposition of hundreds of chemical species across regional to global scales. Three open-source models dominate the research landscape: **GEOS-Chem** from Harvard University, **CMAQ** from the U.S. Environmental Protection Agency, and **CAM-Chem** from the National Center for Atmospheric Research (NCAR). Each serves different scales, research communities, and policy applications.

This comparison examines deployment considerations, chemical mechanisms, computational requirements, and real-world applications of these self-hosted atmospheric chemistry modeling systems.

## Model Overview

| Feature | GEOS-Chem | CMAQ | CAM-Chem |
|---------|-----------|------|----------|
| **Primary Focus** | Global tropospheric chemistry | Regional air quality | Global chemistry-climate |
| **Stars** | 232 | 357 | 89 |
| **Scale** | Global (0.25°-4°) | Regional (1-36 km) | Global (0.25°-1°) |
| **Developer** | Harvard / Dalhousie | US EPA | NCAR |
| **License** | MIT | MIT | BSD |
| **Language** | Fortran | Fortran | Fortran |
| **Chemistry** | Full tropospheric O₃-NOₓ-HC-aerosol | Full gas + aerosol + aqueous | Tropospheric + stratospheric |
| **Input Data** | MERRA-2 / GEOS-FP | WRF / meteorological | CESM / reanalysis |
| **Output Format** | netCDF | netCDF / I/O API | netCDF |

## GEOS-Chem: Global Tropospheric Chemistry Benchmark

GEOS-Chem is the most widely used global 3D chemical transport model for tropospheric chemistry. Its "Science Codebase" repository contains the core chemical mechanisms, emission inventories, and transport algorithms used by hundreds of research groups worldwide.

**Key features:**
- Detailed O₃-NOₓ-VOC chemistry with >200 species and >500 reactions
- Comprehensive aerosol microphysics (sulfate, nitrate, ammonium, organic carbon, black carbon, sea salt, dust)
- Mercury chemistry (Hg⁰/Hg²⁺ cycling and deposition)
- Persistent organic pollutant (POP) transport
- Wet and dry deposition schemes
- Online and offline coupling options

**Server deployment:**

```bash
# Clone GEOS-Chem Classic
git clone https://github.com/geoschem/geos-chem.git
cd geos-chem

# Build with CMake
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)

# Set up run directory
cd ../run
./createRunDir.sh

# Configure input data paths in input.geos
# Set met field path, emission inventories, initial conditions

# Run a 1-month simulation
./gcclassic --input input.geos
```

GEOS-Chem excels at global-scale studies: tracking transboundary pollution transport, quantifying methane sources using satellite observations, and projecting future air quality under climate change scenarios. Its nested-grid capability allows regional refinement down to 0.25° for source-receptor analysis.

## CMAQ: The EPA's Regional Workhorse

CMAQ (Community Multiscale Air Quality) is the U.S. EPA's flagship model for regional air quality management. It processes emissions through detailed gas-phase chemistry, aerosol dynamics, cloud chemistry, and deposition to produce spatially resolved concentration fields used for regulatory decision-making.

**Key features:**
- CB6, SAPRC07, and RACM2 chemical mechanisms
- Modal (AERO6/AERO7) aerosol modules
- In-line photolysis (JPROC)
- Bidirectional NH₃ flux
- Source apportionment tools (ISAM)
- Decoupled Direct Method (DDM) for sensitivity analysis
- Two-way WRF-CMAQ coupling

**Docker deployment:**

```yaml
version: "3.8"
services:
  cmaq:
    image: cmaq/cmaq:latest
    container_name: cmaq-model
    volumes:
      - ./data:/shared/data
      - ./output:/shared/output
    environment:
      - IOAPI_LOG_WRITE=F
      - WRF_BC_DIR=/shared/data/wrf
      - EMIS_DIR=/shared/data/emissions
      - ICBC_DIR=/shared/data/icbc
    command: run_cctm.csh
```

CMAQ's tight integration with WRF meteorology makes it the standard for regional air quality forecasting. State and local agencies use CMAQ for State Implementation Plans (SIPs), attainment demonstrations, and evaluating emission control strategies. The source apportionment capability is particularly valuable for identifying which sectors (transportation, industry, agriculture) contribute most to ozone and PM2.5 exceedances.

## CAM-Chem: Chemistry-Climate Interactions

CAM-Chem (Community Atmosphere Model with Chemistry) extends NCAR's atmospheric general circulation model with comprehensive chemistry for studying chemistry-climate feedbacks on global to decadal timescales.

**Key features:**
- Full stratospheric and tropospheric chemistry
- Interactive aerosols (MAM4/MAM7)
- Online chemistry-radiation coupling
- Ocean and land surface coupling via CESM
- Multiple chemistry mechanism options (MOZART, TS1, SuperFast)
- Volcanic and biomass burning emission modules
- Whole atmosphere option (WACCM) extending to ~140 km

**Running CAM-Chem:**

```bash
# CAM-Chem runs as part of CESM
git clone https://github.com/ESCOMP/CESM.git
cd CESM

# Run create_newcase
./cime/scripts/create_newcase --case camchem_test   --compset FC2010climo --res f09_f09_mg17   --machine your_machine --compiler gnu

cd camchem_test
./xmlchange CAM_CONFIG_OPTS="-chem trop_strat_mam4_vbs"

# Build and submit
./case.build
./case.submit
```

CAM-Chem is essential for research on stratospheric ozone recovery, the climate impact of short-lived climate forcers (black carbon, methane, tropospheric ozone), and aerosol-cloud interactions. Its coupling with the full CESM earth system framework enables studies that require ocean and land feedbacks.

## Performance and Input Data Comparison

| Aspect | GEOS-Chem | CMAQ | CAM-Chem |
|--------|-----------|------|----------|
| **Typical resolution** | 2°×2.5° global | 12 km CONUS | 1°×1° global |
| **CPU-hours per month** | ~200 | ~500 | ~2,000 |
| **Storage per year** | ~50 GB | ~200 GB | ~500 GB |
| **Input data size** | ~10 GB (met fields) | ~50 GB (met + emissions) | ~100 GB (all forcings) |
| **Parallel scaling** | Up to ~100 cores | Up to ~256 cores | Up to ~512 cores |
| **Community size** | ~300 groups | ~200 groups | ~100 groups |

## Why Self-Host Atmospheric Chemistry Models?

Running atmospheric chemistry models on your own infrastructure is the standard practice in the research community — and for good reasons that extend beyond cost savings.

**Reproducibility and transparency** are fundamental to environmental research that informs regulations affecting public health and billions of dollars in compliance costs. When the EPA uses CMAQ to justify PM2.5 attainment designations, any stakeholder must be able to reproduce the results. Self-hosting the model with versioned input data and configuration files makes this possible. Cloud-based black-box services undermine the transparency that environmental policy requires.

**Custom emission inventories** are essential for local-scale studies. Most global models use default emission inventories (EDGAR, CEDS, NEI), but specific research questions often require local data: a power plant's actual CEMS monitoring data, a port authority's ship emission logs, or agricultural ammonia fluxes from field measurements. Self-hosting allows you to integrate these custom inventories directly — commercial or cloud-based services rarely offer this flexibility.

**Computational control** matters when your research depends on specific model configurations. CMAQ supports multiple chemical mechanisms (CB6, SAPRC07, RACM2) and aerosol modules (AERO6, AERO7) — choosing different combinations produces meaningfully different results. Self-hosting allows you to run sensitivity analyses across mechanism × inventory × meteorology permutations without per-simulation costs.

**Long-term studies** spanning decades of simulation (e.g., 1990-2020 trend analysis) require sustained compute access. A 30-year GEOS-Chem simulation at 2°×2.5° resolution takes approximately 3-4 wall-clock days on 64 cores. Cloud providers charging per core-hour would make such studies prohibitively expensive, while self-hosted HPC clusters incur no marginal cost.

**Data provenance tracking** is critical for research that may face legal scrutiny. Every input dataset (meteorology, emissions, boundary conditions) must be documented with version, download date, and preprocessing steps. Self-hosted workflows with version-controlled run directories and automated metadata generation satisfy these requirements far better than ad-hoc cloud usage.

## Practical Deployment Considerations

All three models share common infrastructure requirements:

```bash
# Essential dependencies (Ubuntu/Debian)
apt-get install -y gfortran netcdf-bin libnetcdff-dev   libopenmpi-dev openmpi-bin libhdf5-dev hdf5-tools   cmake build-essential

# netCDF operators for post-processing
apt-get install -y nco cdo ncl-ncarg

# Python environment for analysis
conda create -n atmos python=3.11
conda activate atmos
conda install -c conda-forge xarray netCDF4 matplotlib cartopy
```

Input data management is often the most challenging aspect. Meteorological fields (MERRA-2 for GEOS-Chem, WRF output for CMAQ, CESM reanalysis for CAM-Chem) range from 10-100 GB per simulation. Plan storage accordingly — a dedicated NAS or parallel filesystem with 10+ TB capacity is recommended for a research group running all three models. For data management strategies, see our guide on [scientific data servers and repositories](../2026-06-10-self-hosted-scientific-data-servers-thredds-erddap-hyrax/).

If your research extends to weather modeling, our [weather forecasting model comparison](../2026-06-08-weather-forecasting-wrf-vs-ufs-vs-wrf-hydro/) covers the meteorological drivers that feed these chemistry models. For molecular-scale chemistry, see our [computational chemistry engines guide](../2026-06-10-self-hosted-computational-chemistry-engines-pyscf-psi4-nwchem/).

## FAQ

### Which model should I use for my research?

Use GEOS-Chem if your research question operates at global or hemispheric scales (intercontinental transport, methane budgets, mercury cycling). Use CMAQ for regional air quality studies, regulatory applications, or source-receptor analysis at city-to-state scales. Use CAM-Chem for chemistry-climate interactions, stratospheric studies, or research requiring coupled ocean-atmosphere feedbacks.

### How do I obtain meteorological input data?

GEOS-Chem uses NASA MERRA-2 or GEOS-FP reanalysis (free registration at NASA GES DISC). CMAQ typically requires WRF output from your own meteorological simulation, though pre-processed test datasets are available. CAM-Chem can use internally generated meteorology (specified dynamics mode) or offline reanalysis fields. All are several GB to tens of GB per simulation month.

### Can these models run on cloud infrastructure?

Yes, all three can run on cloud VMs. However, the I/O patterns (frequent netCDF reads/writes) make them sensitive to storage performance. Use instance-local SSDs, not network-attached storage, for the run directory. AWS ParallelCluster or Azure CycleCloud can replicate HPC-like environments. Budget at minimum a 32-core instance with 128 GB RAM for CMAQ, or 64-core with 256 GB for CAM-Chem.

### How are emissions updated and what inventories are available?

GEOS-Chem includes CEDS (Community Emissions Data System) for anthropogenic emissions, GFED for biomass burning, and MEGAN for biogenic VOCs. CMAQ uses the EPA's NEI (National Emissions Inventory) for U.S. domains and HTAP for global. CAM-Chem can use multiple inventories through CESM's emission preprocessor. All models support user-supplied emission files for custom scenarios.

### What's the difference between online and offline coupling?

Offline coupling (GEOS-Chem, CMAQ standard mode) reads pre-computed meteorological fields from files — chemistry doesn't feed back to meteorology. Online coupling (CAM-Chem, two-way WRF-CMAQ) allows chemistry to affect radiation, clouds, and dynamics — essential for studying aerosol radiative forcing or ozone-climate feedbacks. Online coupling is 2-5× more computationally expensive but necessary for certain research questions.

### How do I validate model output against observations?

All three models have established benchmarking frameworks. GEOS-Chem uses the benchmark simulation protocol (1-month and 1-year standard simulations validated against ozonesondes, aircraft campaigns, and surface networks). CMAQ provides the AMET (Atmospheric Model Evaluation Tool) for statistical comparison with AQS, CASTNET, and IMPROVE observations. CAM-Chem validation follows CESM's diagnostic framework with additional chemistry-focused diagnostics.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Atmospheric Chemistry Models: GEOS-Chem vs CMAQ vs CAM-Chem",
  "description": "Comparison of three open-source atmospheric chemistry transport models: GEOS-Chem for global tropospheric chemistry, CMAQ for regional air quality, and CAM-Chem for chemistry-climate interactions. Covers installation, deployment, performance, and use cases for environmental research.",
  "datePublished": "2026-06-11",
  "dateModified": "2026-06-11",
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
