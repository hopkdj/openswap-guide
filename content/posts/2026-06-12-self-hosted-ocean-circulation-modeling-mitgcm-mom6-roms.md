---
title: "Self-Hosted Ocean Circulation Modeling: MITgcm vs MOM6 vs ROMS Compared"
date: "2026-06-12"
tags: ["ocean-modeling", "scientific-computing", "climate-science", "hpc", "earth-system", "fluid-dynamics", "environmental-modeling"]
draft: false
---

## Introduction

Ocean circulation models are the computational backbone of modern oceanography, climate prediction, and marine resource management. These numerical models simulate the movement of water masses, heat transport, biogeochemical cycles, and sea-level dynamics across scales from coastal estuaries to global ocean basins. While traditionally run on institutional supercomputers, the maturation of open-source ocean models and the availability of powerful HPC hardware now make self-hosted ocean simulation a reality for research labs, consultancies, and citizen science organizations.

This guide compares three leading open-source ocean circulation frameworks — **MITgcm**, **MOM6**, and **ROMS** — examining their architectures, computational requirements, deployment patterns, and ideal use cases for self-hosted environments.

## What Are Ocean Circulation Models?

Ocean General Circulation Models (OGCMs) solve the primitive equations of fluid motion on a rotating sphere: Navier-Stokes momentum conservation, continuity, temperature and salinity transport, and an equation of state for seawater density. They discretize the ocean into three-dimensional grid cells and time-step forward using numerical schemes ranging from explicit finite differences to semi-implicit spectral methods.

Key physical processes these models capture include:

- **Barotropic and baroclinic modes** — fast surface gravity waves (external mode) and slower internal density-driven flows
- **Thermohaline circulation** — the global conveyor belt driven by temperature and salinity gradients
- **Mesoscale eddies** — turbulent features at 10–100 km scales that dominate ocean kinetic energy
- **Boundary layer physics** — surface wind stress, bottom friction, and coastal upwelling
- **Tracer transport** — advection and diffusion of heat, salt, carbon, nutrients, and biogeochemical tracers

The computational challenge is immense: a global 1/12° resolution simulation (~9 km grid spacing) produces petabytes of output and requires thousands of CPU cores for months. Even regional models at 1–5 km resolution demand significant HPC resources. Self-hosted deployments typically target regional-scale studies, process-oriented experiments, or educational/demonstration runs on workstation-class hardware.

## Comparison Table

| Feature | MITgcm | MOM6 | ROMS |
|---------|--------|------|------|
| **Primary Developer** | MIT / NASA JPL | NOAA-GFDL | Rutgers / UCLA |
| **Stars** | 401+ | 219+ | 72+ |
| **Last Updated** | May 2026 | May 2026 | Sep 2021 |
| **Grid Type** | Curvilinear, cubed-sphere, lat-lon | Arakawa C-grid, generalized vertical | Terrain-following (sigma/s-coordinate) |
| **Primary Applications** | Global climate, regional, coastal, atmosphere | Global ocean climate, coupled Earth System | Regional, coastal, estuarine |
| **Parallelization** | MPI + OpenMP | MPI (FMS coupler) | MPI + OpenMP |
| **Horizontal Discretization** | Finite volume | Finite volume (Arakawa C-grid) | Finite difference (Arakawa C-grid) |
| **Vertical Coordinate** | z*, p*, terrain-following (flexible) | Hybrid (isopycnal, z*, sigma) | Terrain-following (sigma/s-coordinate) |
| **Non-hydrostatic** | Yes (optional) | No | Yes |
| **Sea Ice** | Yes (dynamic/thermodynamic) | Yes (SIS2) | Yes (via coupling) |
| **Biogeochemistry** | Yes (multiple packages) | Yes (generic tracer framework) | Yes (multiple packages) |
| **Data Assimilation** | Yes (adjoint-based, 4D-Var) | Yes (via JEDI) | Yes (4D-Var, ensemble) |
| **Language** | Fortran 77/90 | Fortran 90 | Fortran 90 |
| **License** | MIT | LGPL 3.0 | MIT/BSD |
| **Self-Hosting Difficulty** | High (build system complexity) | Moderate (FMS framework) | Low-Moderate (simpler build) |

## MITgcm: The Versatile Workhorse

MITgcm (MIT General Circulation Model) is one of the most versatile ocean models ever developed. Originally designed for ocean circulation studies, it has evolved into a general-purpose fluid dynamics solver capable of simulating everything from laboratory-scale convection experiments to planetary atmospheres.

### Key Strengths

MITgcm's unique advantage is its **non-hydrostatic capability** — it can resolve vertical accelerations that hydrostatic models approximate away. This enables simulation of convection, internal wave breaking, dense overflows, and small-scale turbulence. The model also features an **automated adjoint compiler (TAF)** that generates the adjoint code needed for 4D-Var data assimilation and sensitivity analysis — a capability that has made it the platform of choice for state estimation projects like ECCO (Estimating the Circulation and Climate of the Ocean).

### Installation on Linux

```bash
# Prerequisites for MITgcm on Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y gfortran make mpich libmpich-dev     libnetcdf-dev libnetcdff-dev libopenmpi-dev openmpi-bin     csh tcsh python3 python3-pip

# Clone and configure
git clone https://github.com/MITgcm/MITgcm.git
cd MITgcm
# Choose verification experiment (e.g., global ocean at 4°)
cd verification/global_ocean.cs32x15/
# Set build options
mkdir build && cd build
../../../tools/genmake2 -mods ../code -mpi -of ../../../tools/build_options/linux_amd64_gfortran
make depend
make -j$(nproc)
# Run with 4 MPI processes
mpirun -np 4 ./mitgcmuv
```

### Docker Deployment for Self-Hosting

MITgcm does not ship with an official Dockerfile, but a containerized build can be constructed:

```dockerfile
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y     gfortran make mpich libmpich-dev libnetcdf-dev     libnetcdff-dev libopenmpi-dev openmpi-bin csh python3
RUN git clone https://github.com/MITgcm/MITgcm.git /opt/mitgcm
WORKDIR /opt/mitgcm
# Build a default verification experiment
RUN cd verification/global_ocean.cs32x15 &&     mkdir build && cd build &&     ../../../tools/genmake2 -mods ../code -mpi &&     make depend && make -j4
ENTRYPOINT ["mpirun", "--allow-run-as-root", "-np", "4", "./mitgcmuv"]
```

## MOM6: NOAA's Next-Generation Climate Engine

MOM6 (Modular Ocean Model 6) is NOAA-GFDL's flagship ocean model, powering CMIP6-class Earth System Models including GFDL's ESM4 and OM4. It is the ocean component of multiple U.S. climate models and integrates through the Flexible Modeling System (FMS) coupler framework.

### Key Strengths

MOM6's standout feature is its **generalized vertical coordinate**: the model can dynamically switch between geopotential (z*), isopycnal (density-following), and terrain-following (sigma) coordinates within a single simulation. This "hybrid coordinate" approach gives it exceptional fidelity in representing both surface mixed layer processes (best captured in z*) and deep adiabatic flows (best captured in isopycnal). The SIS2 sea ice model is tightly integrated, and the generic tracer framework makes adding new biogeochemical and ecological modules straightforward.

MOM6 is also central to NOAA's Unified Forecast System (UFS), meaning research-quality model configurations are publicly available and well-documented.

### Installation

```bash
# Prerequisites
sudo apt-get install -y gfortran make libnetcdf-dev libnetcdff-dev     libmpich-dev mpich openmpi-bin libopenmpi-dev pkg-config autoconf

# Clone MOM6 with FMS framework
git clone https://github.com/mom-ocean/MOM6.git
cd MOM6

# Build with autoconf (recommended)
autoreconf -i
./configure --with-netcdf --with-mpi
make -j$(nproc)

# Alternative: build with mkmf (GFDL-style)
mkdir build && cd build
../src/mkmf/bin/list_paths -l ../src ./ ../config_src/dynamic
../src/mkmf/bin/mkmf -t ../src/mkmf/templates/linux-gnu.mk -p MOM6 -c "-Duse_netCDF -Duse_libMPI" path_names
make -j$(nproc)
```

The model reads a `MOM_override` parameter file and NetCDF input grids. NOAA provides standard configurations for global 1/4° and 1/2° resolutions.

## ROMS: The Regional Coastal Specialist

ROMS (Regional Ocean Modeling System) is the premier model for coastal, estuarine, and shelf-scale oceanography. Used by hundreds of research groups worldwide, it excels at resolving complex bathymetry, tidal forcing, river plumes, and air-sea interaction at kilometer-to-subkilometer scales.

### Key Strengths

ROMS uses **terrain-following sigma coordinates** with sophisticated stretching functions that concentrate vertical resolution near the surface and bottom boundary layers. This makes it uniquely capable of resolving both surface Ekman dynamics and benthic boundary layer processes simultaneously. Its **split-explicit time stepping** separates the fast barotropic mode (2D depth-averaged) from the slower baroclinic mode (3D), achieving good computational efficiency on modest hardware.

ROMS includes an extensive ecosystem of coupled modules: sediment transport (CSTMS), wave-current interaction (SWAN coupling), sea ice, and multiple biogeochemical models (NPZD, NEMURO, EcoSim). Its adjoint-based 4D-Var data assimilation system is among the most mature in the regional modeling community.

### Installation

```bash
# Prerequisites
sudo apt-get install -y gfortran make libnetcdf-dev libnetcdff-dev     libopenmpi-dev openmpi-bin subversion perl

# ROMS uses Subversion
svn checkout --username anonymous https://www.myroms.org/svn/src/trunk ROMS
cd ROMS

# Choose an application (e.g., upwelling test case)
export ROMS_APPLICATION=UPWELLING
# Edit Compilers/Linux-gfortran.mk for your system
# Build
make -j$(nproc)
# Run
mpirun -np 4 ./oceanM ROMS/External/roms_upwelling.in
```

**Note:** ROMS requires registration on myroms.org but the source code is freely available under MIT/BSD license. The last commit to the main public repository was in 2021, but the model remains actively maintained through the distributed ROMS community — individual research groups maintain their own forks with the latest physics and numerics.

## Self-Hosting Considerations

### Hardware Requirements

| Scale | Resolution | Grid Points | Min Cores | RAM | Storage/Year |
|-------|-----------|-------------|-----------|-----|--------------|
| **Test** | 1° global | ~10⁶ | 4 | 8 GB | ~1 GB |
| **Regional** | 5 km | ~10⁷ | 16–32 | 64 GB | ~100 GB |
| **Coastal** | 1 km | ~10⁸ | 64–128 | 256 GB | ~1 TB |
| **Eddy-resolving** | 1/12° global | ~10⁹ | 1,000+ | 1 TB+ | ~100 TB+ |

For self-hosting, target regional or coastal configurations. A workstation with 32–64 cores (dual AMD EPYC or Intel Xeon), 256 GB RAM, and fast NVMe storage can run 5 km regional simulations for multi-year integrations.

### Containerized HPC Environment

For a reproducible self-hosted setup, combine the models with MPI and NetCDF in a consistent container:

```yaml
version: '3.8'
services:
  ocean-modeling:
    image: ubuntu:22.04
    container_name: ocean-sim
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    volumes:
      - ./model_data:/data
      - ./output:/output
      - ./configs:/configs
    environment:
      - OMP_NUM_THREADS=4
      - MPI_NUM_PROCS=8
    entrypoint: ["/bin/bash"]
    stdin_open: true
    tty: true
```

For GPU-accelerated ocean modeling (e.g., ROMS CUDA port), use NVIDIA's HPC containers as a base.

## Choosing the Right Model

**Choose MITgcm if:**
- You need non-hydrostatic physics (convection, internal waves, overflows)
- Adjoint sensitivity analysis or 4D-Var state estimation is critical
- You're studying processes from laboratory to planetary scales
- You want maximum flexibility in grid and coordinate design

**Choose MOM6 if:**
- You're contributing to climate-scale Earth System Modeling
- Hybrid vertical coordinates matter for your science (e.g., overflow parameterization)
- You need tight sea-ice coupling
- You want a well-documented, NOAA-supported modeling framework
- You're integrating with the Unified Forecast System (UFS)

**Choose ROMS if:**
- You're focused on coastal, estuarine, or shelf-scale dynamics
- High-fidelity boundary layer resolution is critical
- You need coupled sediment transport or biogeochemistry
- You're working with tidal, river plume, or upwelling-dominated systems
- You want a gentler learning curve with extensive community tutorials

## Why Self-Host Your Ocean Model?

Running ocean models on your own infrastructure offers several unique advantages over cloud HPC or institutional cluster dependencies. First, **data sovereignty** — ocean simulations produce terabytes of output that you own and control locally, with no egress fees or storage quotas. Second, **cost predictability** — while cloud HPC can run $2–4 per core-hour, a self-hosted 64-core workstation amortizes to pennies per core-hour over its lifespan. Third, **workflow reproducibility** — containerized model environments ensure your 2026 simulation can be exactly reproduced in 2030, critical for scientific rigor. Fourth, **educational value** — graduate students and early-career researchers gain systems administration and HPC skills that are increasingly rare in cloud-centric training. Fifth, **iterative exploration** — fast local turnaround on parameter sensitivity studies enables the kind of creative, exploratory science that queue-waiting on shared clusters discourages.

For more on Earth System workflows, see our [climate data servers guide](../2026-06-11-climate-data-servers-thredds-esgf-erddap-guide/). If you're interested in coupled Earth System models, check our [atmospheric chemistry modeling comparison](../2026-06-11-self-hosted-atmospheric-chemistry-models-geoschem-cmaq-camchem/). For managing large-scale simulation outputs, our [scientific workflow management guide](../2026-06-12-self-hosted-scientific-workflow-management-pegasus-toil-cctools/) covers Pegasus, Toil, and CCTools.

## FAQ

### Can I run these models on a single workstation, or do I need a cluster?

For regional and coastal configurations (5–10 km resolution), a single 32–64 core workstation with sufficient RAM (128–256 GB) is adequate. ROMS is the least resource-intensive and can run useful coastal domains on a 16-core machine. MITgcm and MOM6 at global 1/4° resolution require 128+ cores and are better suited for small clusters. All three models support MPI, so you can start on a single node and scale to a cluster as your research demands grow.

### Which model has the gentlest learning curve?

ROMS has the most extensive community documentation, tutorials, and a dedicated user forum. Its clean Fortran 90 codebase and well-defined application templates make it easier for newcomers. MITgcm has the steepest learning curve due to its build system complexity and vast configuration space. MOM6 sits in the middle — it benefits from NOAA's investment in documentation but still requires comfort with the FMS framework and coupler-based workflow.

### Do I need GPU hardware for ocean modeling?

Currently, all three models primarily target CPU clusters with MPI parallelism. GPU acceleration is under active development: ROMS has an experimental CUDA port, and MOM6 developers are exploring OpenACC directives. For self-hosted setups, invest in core count and memory bandwidth rather than GPUs. A dual-socket EPYC system with 8 memory channels provides better ocean modeling performance than a GPU-heavy workstation.

### How do these models handle coupled simulations (ocean-atmosphere)?

MOM6 is designed for coupled Earth System Models through the FMS coupler and integrates with GFDL atmospheric models (AM4), land (LM4), and sea ice (SIS2). MITgcm can run atmosphere and ocean components within the same executable (unified code) or couple externally through OASIS3-MCT. ROMS couples with atmospheric models (WRF, COAMPS) and wave models (SWAN) primarily through the COAWST framework. For self-hosted coupled runs, start with ROMS-SWAN coupling which is well-documented and runs on modest hardware.

### What about model validation and benchmark datasets?

All three models maintain standard test cases. The [OMIP (Ocean Model Intercomparison Project)](https://www.climate.oma.be/RESTOM/) provides standardized forcing datasets and diagnostics. CORE-II and JRA55-do atmospheric forcing datasets are the community standard for standalone ocean simulations. ROMS includes 12+ verification test cases in its distribution. MITgcm's `verification/` directory contains 100+ documented experiments. MOM6 validates against OMIP protocols and NOAA operational standards.

### Are there alternatives to these three models I should know about?

Yes. **NEMO** (Nucleus for European Modelling of the Ocean, gitlab.mercator-ocean.fr) is widely used in European climate centers and powers CMIP6 models including UKESM and EC-Earth. **FVCOM** (Finite-Volume Community Ocean Model) uses unstructured grids for complex coastlines. **CROCO** (Coastal and Regional Ocean Community model) is a modern ROMS fork with improved numerics and active development. For educational and lightweight applications, **Veros** is a pure-Python ocean model with NumPy/JAX backends that runs on laptops. These may warrant separate comparison, but MITgcm, MOM6, and ROMS represent the mature, community-standard options for self-hosted research production.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Ocean Circulation Modeling: MITgcm vs MOM6 vs ROMS Compared",
  "description": "Comprehensive comparison of MITgcm, MOM6, and ROMS for self-hosted ocean circulation modeling. Covers installation, Docker deployment, hardware requirements, and use cases for regional and global ocean simulations.",
  "datePublished": "2026-06-12",
  "dateModified": "2026-06-12",
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
