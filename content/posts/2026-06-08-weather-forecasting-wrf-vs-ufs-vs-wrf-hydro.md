---
title: "Self-Hosted Weather Forecasting: WRF vs UFS vs WRF-Hydro Model Comparison"
date: "2026-06-08"
tags: ["weather", "meteorology", "wrf", "ufs", "forecasting", "atmospheric-modeling", "climate", "scientific-computing", "hpc"]
draft: false
---

## Introduction

Numerical Weather Prediction (NWP) models are the computational engines behind every weather forecast — from your smartphone's weekend outlook to hurricane evacuation orders. These models solve complex atmospheric physics equations on supercomputers, simulating how temperature, pressure, wind, and moisture evolve over time. Self-hosting a weather model gives meteorological researchers, aviation operators, and renewable energy forecasters complete control over forecast resolution, domain, and update frequency.

This guide compares three leading open-source NWP systems: **WRF** (Weather Research and Forecasting), the most widely used research-grade atmospheric model; **UFS** (Unified Forecast System), NOAA's next-generation operational forecasting platform; and **WRF-Hydro**, the hydrological extension that couples atmospheric predictions with streamflow and flood modeling.

## Comparison Table

| Feature | WRF | UFS Weather Model | WRF-Hydro |
|---------|-----|-------------------|-----------|
| **GitHub Stars** | 1,659 | 189 | 239 |
| **Developer** | NCAR / Community | NOAA / Community | NCAR |
| **Primary Language** | Fortran | Fortran | Fortran / Python |
| **Physics Suites** | ARW Core only | Multiple (FV3 dycore) | Coupled to WRF |
| **Horizontal Resolution** | Down to 1 km | Down to 3 km (global) | Down to 100 m (reach) |
| **Forecast Period** | Hours to weeks | Days to months | Hours to weeks |
| **Parallel Computing** | MPI + OpenMP | MPI + OpenMP | MPI |
| **Container Support** | Docker, Singularity | Singularity, Spack | Docker, Conda |
| **Initial Conditions** | GFS, ERA5, NAM | GFS, GDAS | WRF output + forcing |
| **Post-Processing** | NCL, Python, RIP | UPP (Unified Post) | Python, R |
| **Visualization** | NCAR Graphics, VAPOR | Python, NCL | Python, R, GIS |

## WRF: The Research Community Standard

[WRF](https://github.com/wrf-model/WRF) is the most widely deployed mesoscale weather model in the world, with thousands of research papers, operational deployments, and educational uses spanning two decades. The Advanced Research WRF (ARW) dynamic core supports grid nesting for high-resolution regional simulations within coarser global domains.

### Key Strengths

WRF's greatest asset is its physics diversity. The model ships with over a dozen parameterization schemes for microphysics, cumulus convection, planetary boundary layer, longwave/shortwave radiation, and land surface processes. This allows researchers to test different physics combinations for specific phenomena — from severe thunderstorms to urban heat islands.

The WRF Preprocessing System (WPS) handles ingestion of initial and boundary conditions from global models (GFS, ERA5, CFS) and static geographic data (terrain, land use, soil type). The preprocessing workflow is well-documented with thousands of tutorials, making WRF accessible despite its complexity.

### Deployment

WRF is typically deployed on HPC clusters using MPI for parallel execution. Here is a basic compilation workflow:

```bash
# Download and compile WRF
git clone https://github.com/wrf-model/WRF.git
cd WRF
./configure  # Select GNU compilers with dmpar
./compile em_real >& compile.log &

# Run a test case
cd test/em_real
./ideal.exe
mpirun -np 4 ./wrf.exe
```

For Docker-based testing:

```yaml
version: "3"
services:
  wrf:
    image: ncote/wrf-docker:latest
    volumes:
      - ./wrf_data:/WRF/data
      - ./wrf_output:/WRF/output
    environment:
      OMP_NUM_THREADS: 4
      WRF_CORES: 8
    command: >
      bash -c "
      cd /WRF/WRF/run &&
      ln -sf /WRF/data/wrfinput_d01 . &&
      ln -sf /WRF/data/wrfbdy_d01 . &&
      mpirun -np 8 ./wrf.exe
      "
```

## UFS: NOAA's Next-Generation Forecast System

The [Unified Forecast System (UFS)](https://github.com/UFS-Community/ufs-weather-model) represents NOAA's strategic consolidation of multiple operational forecast models into a single, community-developed framework. Built around the Finite-Volume Cubed-Sphere (FV3) dynamical core — the same engine that powers the GFS global model — UFS aims to unify global, regional, hurricane, air quality, and space weather prediction under one architecture.

### Key Strengths

UFS's primary advantage is its direct lineage to NOAA operations. Improvements validated by the community feed directly into the models that produce official NWS forecasts. The Common Community Physics Package (CCPP) provides a standardized interface for physics parameterizations, enabling researchers to develop new physics schemes testable in both UFS and other CCPP-compatible models.

The Earth System Modeling Framework (ESMF) and NUOPC layer enable UFS to couple with ocean (MOM6), wave (WW3), sea ice (CICE), and land surface (Noah-MP) models, supporting fully coupled Earth system predictions. This capability is particularly valuable for hurricane intensification studies and seasonal climate forecasts.

### Deployment

UFS uses Spack for dependency management and Singularity containers for reproducible environments:

```bash
# Build UFS using Spack and Singularity
git clone https://github.com/UFS-Community/ufs-weather-model.git
cd ufs-weather-model

singularity build ufs.sif docker://noaaepic/ubuntu20.04-intel-ufs:latest
singularity exec ufs.sif bash -c "./build.sh"

# Run a regional forecast
cd tests/regional
singularity exec ufs.sif bash -c "mpirun -np 36 ufs_model"
```

## WRF-Hydro: Hydrological Forecasting

[WRF-Hydro](https://github.com/NCAR/wrf_hydro_nwm_public) extends WRF's atmospheric modeling with hydrological routing, enabling predictions of streamflow, soil moisture, groundwater, and flood inundation. It powers the National Water Model (NWM), which provides streamflow forecasts for 2.7 million river reaches across the continental United States.

### Key Strengths

WRF-Hydro solves a critical gap in pure atmospheric models: what happens to precipitation once it hits the ground. The model routes water through surface, subsurface, and channel networks using diffusive wave and Muskingum-Cunge routing schemes. For flood-prone regions, WRF-Hydro can be configured at 100-meter resolution along river reaches, producing street-level flood forecasts.

The model supports both offline (meteorological forcing data) and coupled (WRF output) modes. In coupled mode, WRF-Hydro feeds soil moisture and evapotranspiration back to the atmospheric model, closing the land-atmosphere feedback loop and improving precipitation forecasts.

### Deployment

WRF-Hydro uses Python-based configuration and NetCDF I/O:

```bash
# Clone and set up
git clone https://github.com/NCAR/wrf_hydro_nwm_public.git
cd wrf_hydro_nwm_public/trunk/NDHMS

# Configure with Python preprocessing
python3 WrfHydroGIS.py --domain domain.nc --forcing forcing/ --output output/

# Compile and run
./configure
make
mpirun -np 8 ./wrf_hydro.exe
```

## Choosing the Right Weather Model

- **Choose WRF** if you need the most flexible, well-documented mesoscale model with the largest user community. Best for academic research, regional forecasting, and operational meteorology at 1-45 km resolutions.
- **Choose UFS** if you need NOAA operational compatibility, global forecasting capability, or coupled Earth system predictions (atmosphere-ocean-wave-ice). It is the future of U.S. operational weather prediction.
- **Choose WRF-Hydro** if streamflow, flood forecasting, or water resource management is your primary concern. It adds hydrological routing to atmospheric predictions.

## Why Self-Host a Weather Model?

Cloud-based weather APIs (OpenWeatherMap, Tomorrow.io, WeatherStack) provide convenient forecasts at the cost of resolution, customization, and refresh frequency. A self-hosted WRF or UFS model running on your own infrastructure can produce forecasts at 1 km resolution every hour — vastly superior to the 0.25-degree (about 25 km), 6-hourly updates from most free APIs. For applications like wind farm power prediction, wildfire spread modeling, or precision agriculture, this resolution difference translates directly to operational decisions.

Data sovereignty is another driver. Meteorological data — particularly high-resolution terrain and land-use inputs — can be subject to export controls or licensing restrictions. Self-hosting ensures compliance with institutional data policies and eliminates dependency on external API availability during severe weather events when forecasts are most critical.

For those already running self-hosted weather station hardware, see our [weather station software guide](../self-hosted-weather-station-software-weewx-meteobridge-weather34-guide/) for integrating observational data with model output. For upper-air observation enthusiasts, our [weather balloon radiosonde tracking guide](../self-hosted-weather-balloon-radiosonde-tracking-radiosonde-auto-rx-guide/) covers complementary hardware for model validation.

## FAQ

### What hardware do I need to run WRF?

For a small regional domain (100x100 grid points, 48-hour forecast): at minimum a 16-core server with 64GB RAM and 500GB SSD storage. Realistic regional forecasts (500x500 grid points) require HPC-class hardware: 128+ cores, 256GB+ RAM, and InfiniBand interconnects for MPI communication.

### How long does it take to run a forecast?

A 48-hour forecast on a 500x500 domain with 36 vertical levels takes approximately 2-4 hours on 128 cores depending on physics complexity. Real-time operational forecasts require the model to run faster than wall-clock time. UFS at global 13 km resolution runs in under 1 hour on 1,000+ cores on NOAA's operational supercomputers.

### Where do I get initial condition data?

GFS forecast data (0.25-degree, 3-hourly) is freely available from NOAA's NOMADS server via HTTP or FTP. ERA5 reanalysis data is available from the Copernicus Climate Data Store with registration. Both are commonly used to initialize WRF and UFS regional domains.

### Can I run weather models on cloud infrastructure?

Yes. AWS ParallelCluster, Azure CycleCloud, and Google Cloud HPC Toolkit provide managed HPC environments suitable for WRF and UFS. Spot/preemptible instances can reduce costs for non-time-critical research runs. A 48-hour, 500x500 WRF run costs approximately $50-100 on AWS c5n.18xlarge spot instances.

### What is the learning curve for weather modeling?

Significant. WRF requires familiarity with Fortran, MPI, NetCDF data formats, meteorological data sources, and physics parameterization theory. Plan for 2-4 weeks to complete your first successful forecast run, even with existing Linux/HPC skills. UFS aims to reduce this barrier with better documentation and containerization.

---

**OpenSwap Guide** helps you discover and deploy self-hosted alternatives to proprietary software. Check our full catalog for more comparisons.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Weather Forecasting: WRF vs UFS vs WRF-Hydro Model Comparison",
  "description": "Compare three leading open-source numerical weather prediction systems: WRF, UFS, and WRF-Hydro. Includes deployment guides, hardware requirements, and selection criteria for meteorological research and operational forecasting.",
  "datePublished": "2026-06-08",
  "dateModified": "2026-06-08",
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
