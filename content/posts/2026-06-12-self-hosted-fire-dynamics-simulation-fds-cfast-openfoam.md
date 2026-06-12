---
title: "Self-Hosted Fire Dynamics Simulation: FDS vs CFAST vs OpenFOAM"
date: "2026-06-12"
tags: ["fire-simulation", "fire-dynamics", "cfd", "fire-safety", "fds", "cfast", "openfoam", "fire-engineering"]
draft: false
---

## Introduction

Fire dynamics simulation is a critical tool for fire protection engineers, building code consultants, and safety researchers. Computational fire models predict smoke movement, temperature distributions, toxic gas concentrations, and structural response during fire events — enabling performance-based design that goes beyond prescriptive building codes. From atrium smoke management systems to tunnel ventilation design, these simulations save lives by validating safety systems before construction begins.

The open-source ecosystem provides three complementary approaches to fire modeling: **FDS** (Fire Dynamics Simulator) by NIST for high-fidelity computational fluid dynamics, **CFAST** (Consolidated Fire and Smoke Transport) also by NIST for fast two-zone compartment modeling, and **OpenFOAM** as a general-purpose CFD platform with fire-specific solvers. This article compares their capabilities, deployment patterns, and appropriate use cases for self-hosted fire engineering workflows.

## Comparison Table

| Feature | FDS | CFAST | OpenFOAM |
|---------|-----|-------|----------|
| **Developer** | NIST (US) | NIST (US) | OpenFOAM Foundation |
| **Stars** | 839⭐ | 88⭐ | 2,113⭐ |
| **Language** | Fortran | C / C++ | C++ |
| **Model Type** | CFD (LES) | Two-Zone Model | CFD (RANS/LES) |
| **Grid** | Structured rectilinear | Zone-based | Unstructured polyhedral |
| **Combustion** | Mixture fraction + finite-rate | Species-based | Multiple solvers |
| **Radiation** | Finite Volume Method | Radiative fraction | fvDOM / P1 |
| **Soot/Smoke** | Detailed soot model | Empirical yield | Lagrangian/Eulerian |
| **Sprinklers** | Lagrangian particles | None | Custom implementation |
| **HVAC Networks** | Built-in HVAC solver | Duct network model | Custom via solvers |
| **Parallel** | MPI (excellent scaling) | Single CPU | MPI (excellent scaling) |
| **Visualization** | Smokeview | Smokeview (via FDS) | ParaView |
| **Simulation Speed** | Hours to days | Seconds to minutes | Hours to days |
| **License** | Public Domain | Public Domain | GPL v3 |
| **Pyrolysis Model** | Yes (solid phase) | Yes (simplified) | Custom |

## FDS: High-Fidelity Fire CFD

FDS is a computational fluid dynamics model of fire-driven fluid flow developed at the National Institute of Standards and Technology (NIST). It solves a form of the Navier-Stokes equations appropriate for low-speed, thermally-driven flow with an emphasis on smoke and heat transport from fires. FDS uses Large Eddy Simulation (LES) for turbulence closure, providing spatially and temporally resolved predictions of temperature, velocity, and species concentrations.

FDS has been extensively validated against full-scale fire experiments and is accepted by regulatory bodies worldwide for performance-based design. It is the reference tool for complex fire scenarios including:

- Warehouse and industrial facility fire protection
- Tunnel ventilation and smoke control
- Atrium smoke management systems
- Nuclear facility fire hazard analysis
- Aircraft hangar suppression systems

### Installing and Running FDS

```bash
# Download from NIST
wget https://github.com/firemodels/fds/releases/download/FDS6.9.0/FDS6.9.0_SMV6.9.0_linux64.tar.gz
tar -xzf FDS6.9.0_SMV6.9.0_linux64.tar.gz
export PATH=$PATH:$(pwd)/FDS6/bin

# Run a simulation
fds my_fire_scenario.fds
```

### Docker Compose for HPC Simulation

FDS excels in parallel execution across multiple CPUs. For self-hosted simulation servers:

```yaml
version: "3.8"
services:
  fds-simulator:
    image: firemodels/fds:6.9.0
    volumes:
      - ./scenarios:/simulations
      - ./output:/output
    environment:
      - OMP_NUM_THREADS=4
    command: >
      mpiexec -np 8 fds /simulations/warehouse_fire.fds
    deploy:
      resources:
        limits:
          cpus: "8"
          memory: 16G
```

A typical FDS input file defines the computational domain, geometry (as obstructions), material properties, fire source, and output quantities:

```
&HEAD CHID='warehouse_fire', TITLE='Warehouse Fire Scenario' /
&MESH IJK=120,80,40, XB=0.0,30.0,0.0,20.0,0.0,10.0 /
&TIME T_END=600.0 /
&REAC ID='POLYURETHANE', FUEL='REAC_FUEL',
      SOOT_YIELD=0.10, CO_YIELD=0.042 /
&SURF ID='Burner', HRRPUA=1000.0, COLOR='RED' /
&VENT XB=10.0,15.0,7.0,10.0,0.0,0.0, SURF_ID='Burner' /
&OBST XB=5.0,8.0,4.0,8.0,0.0,3.0, SURF_ID='CONCRETE' /
&VENT XB=0.0,0.0,0.0,20.0,0.0,10.0, SURF_ID='OPEN' /
&SLCF PBY=10.0, QUANTITY='TEMPERATURE' /
&TAIL /
```

## CFAST: Two-Zone Compartment Modeling

CFAST is a two-zone fire model that divides each compartment into an upper hot gas layer and a lower cool gas layer, tracking heat and mass transfer between zones, compartments, and the environment. While less spatially detailed than CFD, CFAST solves in seconds to minutes — making it ideal for probabilistic risk assessment, parametric studies, and design iterations where hundreds or thousands of scenarios must be evaluated.

The two-zone assumption is surprisingly accurate for pre-flashover compartment fires because thermal stratification creates a relatively sharp interface between the hot smoke layer and the cooler lower layer. CFAST models:

- Fire plume entrainment (McCaffrey, Heskestad correlations)
- Ceiling jet flow and heat transfer
- Radiation exchange between layers and surfaces
- Mechanical ventilation and HVAC duct networks
- Multiple compartments with horizontal and vertical openings
- Species tracking (O₂, CO₂, CO, HCN, soot)
- Sprinkler and detector activation

### Building and Running CFAST

```bash
git clone https://github.com/firemodels/cfast.git
cd cfast
mkdir build && cd build
cmake ..
make -j4

# Run simulation
./CFAST ../Examples/room_fire.in
```

### Docker Deployment

```yaml
version: "3.8"
services:
  cfast-batch:
    image: ubuntu:24.04
    volumes:
      - ./inputs:/inputs
      - ./outputs:/outputs
    command: >
      bash -c "
      apt-get update && apt-get install -y build-essential cmake gfortran &&
      git clone https://github.com/firemodels/cfast.git &&
      cd cfast/Build/CFAST/intel_linux_64 &&
      make &&
      for f in /inputs/*.in; do ./cfast \$f /outputs/\$(basename \$f .in).csv; done
      "
```

## OpenFOAM: General-Purpose CFD for Fire

OpenFOAM is an open-source computational fluid dynamics toolbox capable of solving complex fluid flows involving chemical reactions, turbulence, and heat transfer. While not fire-specific like FDS, OpenFOAM's modular solver architecture enables fire simulations through specialized solvers and boundary conditions.

The `fireFoam` solver combines compressible Navier-Stokes with combustion and radiation models:

- Eddy Dissipation Concept (EDC) for turbulent combustion
- Finite volume discrete ordinates method (fvDOM) for radiation
- Soot formation and oxidation models
- Lagrangian particle tracking for water droplets (sprinklers)

OpenFOAM's key advantage is its flexibility — users can modify governing equations, add custom physics models, and use arbitrary unstructured meshes for complex geometries that structured-grid FDS cannot easily resolve.

### Installing OpenFOAM

```bash
# Install from package
sudo sh -c "wget -O - https://dl.openfoam.com/add-debian-repo.sh | bash"
sudo apt-get install openfoam2412-default

source /usr/lib/openfoam/openfoam2412/etc/bashrc
```

### Running a Fire Simulation

```bash
cp -r $FOAM_TUTORIALS/combustion/fireFoam/LES/flameSpreadWaterSuppressionPanel .
cd flameSpreadWaterSuppressionPanel
blockMesh
fireFoam
```

## Choosing the Right Tool

The three tools serve different niches in fire engineering:

- **Select FDS** for detailed design verification of life safety systems — tunnel ventilation, atrium smoke exhaust, large warehouse sprinkler design — where spatial resolution, validated fire physics, and regulatory acceptance are paramount. FDS's structured-grid LES approach provides the highest-fidelity predictions but requires significant computational resources and expertise.
- **Select CFAST** for probabilistic risk assessment, parametric studies, and early-stage design exploration where hundreds of fire scenarios must be evaluated quickly. Its two-zone model captures the essential physics of compartment fires at a fraction of the computational cost. CFAST also integrates natively with evacuation models and risk analysis frameworks.
- **Select OpenFOAM** when your fire scenario requires physics beyond standard fire models — complex fuel pyrolysis, water mist suppression, coupled structural-fire analysis — or when geometry demands unstructured meshing that structured FDS cannot accommodate. OpenFOAM's modular architecture enables research-grade customization.

For many fire engineering consultancies, the workflow begins with CFAST for rapid scenario screening, proceeds to FDS for detailed design verification, and reserves OpenFOAM for research problems or unusual geometries that push the limits of specialized fire codes.

For related simulation and visualization tools, see our [scientific simulation comparison](../2026-06-08-self-hosted-scientific-simulation-openfoam-elmer-calculix/) and [scientific data visualization guide](../2026-06-09-self-hosted-scientific-data-visualization-paraview-visit-vtkjs-pyvista/). For HPC deployment, check our [HPC workload managers guide](../2026-05-02-slurm-vs-openpbs-vs-htcondor-self-hosted-hpc-workload-managers-guide/).

## FAQ

**Q: Why use LES instead of RANS for fire simulations?**

Large Eddy Simulation (LES) resolves the large, energy-containing turbulent eddies that govern smoke transport, flame spread, and entrainment — all critical for fire safety predictions. RANS (Reynolds-Averaged Navier-Stokes) models average out these turbulent fluctuations, which under-predicts plume entrainment and smoke filling rates. FDS uses LES by default; OpenFOAM's fireFoam supports both but LES is recommended for fire applications.

**Q: How do I validate a fire simulation against experimental data?**

NIST maintains an extensive validation suite for FDS with hundreds of full-scale experiments covering flame height, ceiling jet temperature, smoke layer descent, and sprinkler activation. CFAST has been validated against compartment fire test series. Validation involves comparing predicted quantities (temperature, heat flux, species concentration) against measured data using metrics like relative difference, model bias, and scatter. Always consult the FDS Validation Guide and document your validation process for regulatory submissions.

**Q: How long does a typical fire simulation take to run?**

CFAST solves in seconds to a few minutes regardless of scenario duration. FDS simulation time scales with mesh resolution, simulation duration, and CPU count. A 10-minute warehouse fire on a 2-million-cell mesh runs approximately 8-24 hours on 16-32 cores. OpenFOAM fire simulations are comparable to FDS for similar mesh sizes. For parametric studies with hundreds of scenarios, the CFAST → FDS pipeline (screen with CFAST, verify with FDS) is the standard efficient workflow.

**Q: Can I model water-based suppression systems?**

FDS has the most sophisticated sprinkler modeling, with Lagrangian particles representing water droplets that exchange mass, momentum, and energy with the gas phase. It models droplet breakup, evaporation, and interaction with fuel surfaces. OpenFOAM supports Lagrangian spray modeling through custom solvers. CFAST models sprinkler activation timing and a global heat extraction rate but does not track individual droplets — sufficient for detection and system activation studies but not for detailed suppression dynamics.

**Q: What are the computational hardware requirements for fire CFD?**

FDS benefits significantly from high single-core performance and good memory bandwidth. A dual-socket server with 16-32 physical cores and 64-128 GB RAM handles most consulting-scale simulations up to 5-10 million cells. For large warehouse or high-rise simulations with 50+ million cells, HPC clusters with InfiniBand interconnects and 128-256 cores are typical. CFAST runs comfortably on any modern workstation with 8 GB RAM.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Fire Dynamics Simulation: FDS vs CFAST vs OpenFOAM",
  "description": "Compare three open-source fire simulation platforms — FDS (Fire Dynamics Simulator), CFAST, and OpenFOAM — with Docker Compose deployment guides, solver comparison, and self-hosting guidance for fire engineering.",
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
