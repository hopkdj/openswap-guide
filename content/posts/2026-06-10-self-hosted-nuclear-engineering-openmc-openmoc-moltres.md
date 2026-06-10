---
title: "Self-Hosted Nuclear Engineering Simulation: OpenMC vs OpenMOC vs Moltres"
date: "2026-06-10"
tags: ["nuclear-engineering", "simulation", "scientific-computing", "hpc", "monte-carlo", "open-science"]
draft: false
---

## Introduction

Nuclear reactor design and safety analysis depend on neutron transport simulations that track billions of particle histories through complex three-dimensional geometries. Three open-source simulation codes serve distinct roles in the nuclear engineering toolkit: **OpenMC** (Monte Carlo neutron transport), **OpenMOC** (Method of Characteristics deterministic transport), and **Moltres** (multi-physics reactor simulation).

Each code addresses different stages of the reactor analysis workflow, from detailed fuel assembly calculations to full-core depletion studies coupled with thermal-hydraulic feedback. This guide compares their capabilities, deployment patterns, and optimal use cases for self-hosted HPC environments.

## Feature Comparison

| Feature | OpenMC | OpenMOC | Moltres |
|---------|--------|---------|---------|
| **Transport Method** | Monte Carlo (stochastic) | Method of Characteristics (deterministic) | Diffusion plus SP3 (deterministic) |
| **GitHub Stars** | 1,033+ | 185+ | 81+ |
| **Current Version** | 0.15.2 | 0.6.2 | Based on MOOSE framework |
| **Energy Treatment** | Continuous energy plus multi-group | Multi-group | Multi-group |
| **Geometry** | Constructive Solid Geometry (CSG) | 2D extruded assemblies | 3D unstructured mesh (via MOOSE) |
| **Thermal-Hydraulic Coupling** | External (via Cardinal/MOOSE) | None | Built-in (Boussinesq approximation) |
| **Depletion/Burnup** | Built-in (ORIGEN API integration) | Through OpenDeplete | Through MOOSE modules |
| **Parallelism** | MPI plus OpenMP hybrid | MPI plus OpenMP | MPI (MOOSE framework) |
| **Nuclear Data** | HDF5 format (from NNDC) | HDF5 multi-group libraries | Multi-group cross sections |
| **Uncertainty Quantification** | Statistical (inherent to Monte Carlo) | None | Via MOOSE stochastic tools |
| **License** | MIT | MIT | LGPL 2.1 |
| **GPU Support** | Experimental (OpenCL backend) | None | Via MOOSE GPU modules |

## Self-Hosted Deployment

Nuclear simulation codes have significant compilation requirements. Docker provides a reproducible environment that handles all dependency chains:

```yaml
# docker-compose.yml — Nuclear Simulation Stack
version: '3.8'
services:
  openmc:
    image: openmc/openmc:latest
    volumes:
      - ./models:/models
      - ./results:/results
      - ./nuclear_data:/nuclear_data
    environment:
      - OPENMC_CROSS_SECTIONS=/nuclear_data/endfb-viii.0-hdf5/cross_sections.xml
      - OMP_NUM_THREADS=8
    command: openmc --threads 8

  openmoc:
    build:
      context: ./openmoc
      dockerfile: Dockerfile
    volumes:
      - ./openmoc-inputs:/inputs
      - ./results:/results
    command: python3 /inputs/assembly_calc.py

  moltres:
    build:
      context: .
      dockerfile: Dockerfile.moltres
    volumes:
      - ./moltres-inputs:/inputs
      - ./results:/results
```

OpenMC requires nuclear data libraries that typically range from 10 to 50 GB depending on the evaluation. Set up the data directory before running any simulations:

```bash
# Download ENDF/B-VIII.0 nuclear data for OpenMC (requires ~25 GB free)
wget https://anl.box.com/shared/static/9igk6p3q8z9v5kf6znk2jqy0hgjy5jxh.h5 \
  -O /nuclear_data/endfb-viii.0-hdf5/lib80x.h5

# Set the environment variable pointing to cross section index
export OPENMC_CROSS_SECTIONS=/nuclear_data/endfb-viii.0-hdf5/cross_sections.xml

# Install OpenMC via conda (simpler than manual compilation)
conda install -c conda-forge openmc
```

### OpenMC: Monte Carlo Neutron Transport

OpenMC performs stochastic neutron transport, tracking individual neutrons through materials using accurate continuous-energy nuclear data. Its statistical approach provides gold-standard reference solutions for reactor physics calculations:

```python
import openmc

# Create a simple PWR fuel pin model with three radial zones
uo2 = openmc.Material(name='UO2')
uo2.add_element('U', 0.033, enrichment=4.0)
uo2.add_element('O', 0.067)
uo2.set_density('g/cm3', 10.97)

zircaloy = openmc.Material(name='Zircaloy-4')
zircaloy.add_element('Zr', 0.98)
zircaloy.add_element('Sn', 0.015)
zircaloy.set_density('g/cm3', 6.56)

water = openmc.Material(name='Water Moderator')
water.add_element('H', 0.067)
water.add_element('O', 0.033)
water.set_density('g/cm3', 0.74)

# Define fuel pin geometry with fuel, gap, and cladding
fuel_or = openmc.ZCylinder(r=0.41)
clad_ir = openmc.ZCylinder(r=0.42)
clad_or = openmc.ZCylinder(r=0.48)

fuel = openmc.Cell(fill=uo2, region=-fuel_or)
gap = openmc.Cell(fill=None, region=+fuel_or & -clad_ir)
clad = openmc.Cell(fill=zircaloy, region=+clad_ir & -clad_or)
moderator = openmc.Cell(fill=water, region=+clad_or)

# Configure simulation settings for eigenvalue calculation
settings = openmc.Settings()
settings.batches = 100
settings.particles = 10000
settings.inactive = 20
settings.source = openmc.IndependentSource(
    space=openmc.stats.Box([-0.41, -0.41, -1], [0.41, 0.41, 1])
)

# Add flux tally with energy filter
tally = openmc.Tally(name='flux spectrum')
tally.filters = [openmc.EnergyFilter([0.0, 0.625e-6, 20.0])]
tally.scores = ['flux', 'fission']

# Build model and run
model = openmc.Model()
model.geometry = openmc.Geometry([fuel, gap, clad, moderator])
model.settings = settings
model.tallies = [tally]
sp_file = model.run()
```

### OpenMOC: Deterministic 2D Transport

OpenMOC uses the Method of Characteristics, a deterministic approach that solves the Boltzmann transport equation along characteristic tracks through the geometry. This provides solutions orders of magnitude faster than Monte Carlo for repeated assembly-level calculations:

```python
import openmoc

# Create 17x17 PWR assembly model
openmoc.log.set_log_level('NORMAL')

# Define materials with 2-group cross sections
uo2_40 = openmoc.Material(name='UO2 4.0% enrichment')
uo2_40.setNumEnergyGroups(2)
uo2_40.setSigmaT([0.5, 1.0])
uo2_40.setSigmaF([0.01, 0.1])
uo2_40.setNuSigmaF([0.025, 0.25])
uo2_40.setChi([1.0, 0.0])

water = openmoc.Material(name='Water moderator')
water.setNumEnergyGroups(2)
water.setSigmaT([0.3, 0.8])
water.setSigmaS([[0.25, 0.0], [0.05, 0.75]])

# Create fuel pin cell
pin = openmoc.Pin()
pin.setNumSectors(8)
pin.addRing(openmoc.Circle(x=0, y=0, radius=0.41), 1)
pin.addRing(openmoc.Circle(x=0, y=0, radius=0.48), 2)
pin.setFill(2, water)

# Build 17x17 lattice with reflective boundaries
lattice = openmoc.Lattice(id=1, width_x=1.26, width_y=1.26)
lattice.setNumX(17)
lattice.setNumY(17)

for i in range(17):
    for j in range(17):
        lattice.setPin(i, j, pin)

# Configure solver with fine ray spacing
solver = openmoc.CPUSolver()
solver.setNumThreads(8)
solver.setSourceConvergenceThreshold(1e-6)
track_generator = openmoc.TrackGenerator(lattice, 32, 0.05)
track_generator.generateTracks()

solver.setTrackGenerator(track_generator)
solver.setGeometry(lattice)
solver.computeEigenvalue()
```

### Moltres: Multi-Physics Coupled Simulation

Moltres extends the MOOSE framework for coupled neutronics and thermal-hydraulics, enabling time-dependent reactor transient analysis with temperature feedback on cross sections:

```
# Moltres input file — simplified 2D reactor model
[Mesh]
  type = GeneratedMesh
  dim = 2
  nx = 50
  ny = 50
  xmin = 0
  xmax = 100
  ymin = 0
  ymax = 100
[]

[Variables]
  [./group1]
    order = FIRST
    family = LAGRANGE
    initial_condition = 1.0
  [../]
  [./group2]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.5
  [../]
  [./temp]
    order = FIRST
    family = LAGRANGE
    initial_condition = 600.0
  [../]
[]

[Kernels]
  [./diff_group1]
    type = MatDiffusion
    variable = group1
    diffusivity = 'diff_coef_1'
  [../]
  [./diff_group2]
    type = MatDiffusion
    variable = group2
    diffusivity = 'diff_coef_2'
  [../]
  [./heat_conduction]
    type = HeatConduction
    variable = temp
  [../]
  [./heat_source]
    type = CoupledForce
    variable = temp
    v = group1
    coef = 1.5e-14
  [../]
[]

[Executioner]
  type = Transient
  dt = 0.1
  num_steps = 100
  solve_type = 'PJFNK'
  petsc_options_iname = '-pc_type -pc_hypre_type'
  petsc_options_value = 'hypre boomeramg'
[]
```

## Performance and Resource Planning

Nuclear simulations are among the most computationally demanding scientific workloads, and each code type presents fundamentally different resource requirements due to their distinct mathematical approaches.

**OpenMC** performance scales primarily with particle count and the desired statistical precision. For a full-core PWR model with 50 million active neutron histories, a single 32-core node requires 4-8 hours to achieve 10 pcm statistical uncertainty on k-effective. Memory usage is dominated by the nuclear data library (approximately 25 GB for ENDF/B-VIII.0 in HDF5 format) plus geometry and tally storage (2-5 GB). OpenMC's hybrid MPI-plus-OpenMP parallelism achieves approximately 85% parallel efficiency up to 256 cores for typical full-core problems. For depletion calculations spanning 50+ burnup steps, distribute burnup regions across MPI ranks, running each step's transport calculation in parallel.

**OpenMOC** trades statistical uncertainty for deterministic accuracy on 2D problems. A full 17x17 PWR assembly with 8 azimuthal angles and 0.05 cm ray spacing requires approximately 15-30 seconds on a 16-core node—orders of magnitude faster than equivalent Monte Carlo calculations. However, memory requirements grow with the number of flat-source regions: a 3D extruded assembly with 50 axial planes uses approximately 16 GB RAM. OpenMOC's 3D capabilities are limited to extruded geometries; it cannot handle general 3D unstructured meshes like those used in advanced reactor designs.

**Moltres** running within MOOSE inherits MOOSE's MPI-based parallelism with automated domain decomposition via libMesh. For a 2D full-core model with 500,000 mesh elements and 2-group diffusion, steady-state eigenvalue calculations complete in 2-5 minutes on 32 cores. Transient simulations with thermal feedback using 1,000 time steps require 30-60 minutes. Memory usage scales with mesh size—approximately 8 bytes per degree of freedom per variable, plus the Jacobian matrix storage in PETSc's compressed sparse row format which can reach 20-40 GB for fine-mesh 3D problems.

## Why Self-Host Nuclear Simulation Infrastructure?

Nuclear engineering simulations involve export-controlled nuclear data and proprietary reactor designs that cannot legally be uploaded to public cloud platforms in many jurisdictions. The ENDF/B nuclear data libraries, while publicly available, require substantial local storage (25-50 GB) and specific directory structures that cloud-based notebook services do not accommodate. Self-hosting ensures compliance with both nuclear data distribution agreements and institutional intellectual property policies, while maintaining full audit trails of every computation.

The computational economics strongly favor on-premises HPC for nuclear simulation. A single OpenMC full-core depletion calculation with 100 burnup steps and 10 million particles per step requires approximately 200,000 core-hours. At institutional cluster rates of $0.01-0.02 per core-hour, this costs $2,000-4,000 total. Equivalent cloud compute on AWS using c5n.18xlarge instances at approximately $3.06 per hour for 72 vCPUs costs roughly $8,500. For design iteration cycles requiring 10-20 such calculations during a reactor development program, self-hosting saves $65,000-130,000 per project—a meaningful fraction of a small modular reactor startup's total computational budget.

Regulatory compliance adds another layer of justification. Nuclear reactor safety analyses submitted to the U.S. Nuclear Regulatory Commission (NRC) or the International Atomic Energy Agency (IAEA) must include detailed documentation of the computational environment—compiler versions, library patches, and operating system configurations. Self-hosted environments with full configuration management (Ansible, Puppet, or Nix) provide auditable, immutable records of the exact software stack used for each safety submission. Cloud platforms' dynamic infrastructure with auto-updating base images makes this level of computational traceability difficult to achieve and nearly impossible to certify under current regulatory frameworks.

For small modular reactor (SMR) startups with limited budgets, self-hosting OpenMC on a single 64-core workstation provides approximately 80% of the simulation capability needed for conceptual design at a one-time hardware cost of $15,000-25,000. This is less than two months of equivalent cloud spending and provides a dedicated resource without queue delays from shared cloud infrastructure or unexpected cost spikes during long-running depletion calculations.

For broader scientific simulation context, see our [materials science simulation guide](../2026-06-09-self-hosted-materials-science-lammps-quantum-espresso-abinit-guide/) covering LAMMPS, Quantum ESPRESSO, and ABINIT. For parallel computing infrastructure, our [HPC MPI implementations comparison](../2026-06-01-self-hosted-hpc-mpi-implementations-openmpi-mpich-mvapich-guide/) covers OpenMPI, MPICH, and MVAPICH. Physics simulation needs may also benefit from our [plasma physics simulation guide](../2026-06-10-self-hosted-plasma-physics-simulation-plasmapy-warpx-picongpu/) covering PlasmaPy, WarpX, and PIConGPU.

## FAQ

### What nuclear data libraries should I use with OpenMC?

OpenMC supports ENDF/B-VIII.0 (latest U.S. evaluated library, released 2018), JEFF-3.3 (European evaluation), and JENDL-5 (Japanese evaluation) in HDF5 format. Download pre-processed libraries from the OpenMC documentation site rather than processing raw ENDF files yourself—processing with NJOY requires expertise and can take days even on powerful hardware. For most light water reactor applications, ENDF/B-VIII.0 provides the best balance of completeness and validation against critical experiment benchmarks. For advanced reactor types such as molten salt reactors or fast spectrum systems, supplement with TENDL nuclear data for isotopes not well-covered in the major evaluated libraries.

### How do I validate my simulation results against experimental data?

OpenMC includes a comprehensive regression test suite comparing against ICSBEP (International Criticality Safety Benchmark Evaluation Project) criticality benchmarks. Run `openmc-run-tests` after installation to verify your build. For production use, benchmark your models against published MCNP or Serpent results for the same geometry and nuclear data library version. OpenMOC validates against the C5G7 MOX benchmark problem—this is included in the examples directory and serves as the standard deterministic transport verification case. Document all validation results in a technical report if submitting to regulators; they will expect traceable evidence that your simulation methodology produces results within accepted uncertainty bounds.

### Can OpenMC and OpenMOC be used together in a complementary workflow?

Yes, this is a common and effective pattern in reactor design. Use OpenMOC for rapid parametric studies—varying pin enrichment, pitch, and burnable poison configurations—because its deterministic method provides solutions in seconds rather than hours. Once you have identified the most promising configurations, validate them with OpenMC's Monte Carlo method for high-accuracy results that account for resonance self-shielding and continuous-energy effects. Finally, feed the validated configuration into depletion calculations tracking fuel composition over multiple cycles. OpenMC's Python API allows you to programmatically generate geometry variations and batch-submit simulation jobs to your HPC scheduler, creating fully automated design optimization pipelines.

### What are the licensing implications for commercial use?

OpenMC and OpenMOC both use the MIT License—the most permissive open-source license, allowing commercial use, modification, and redistribution with minimal restrictions. This means reactor vendors can incorporate these codes into proprietary design workflows without any copyleft obligations. Moltres uses LGPL 2.1 through its dependency on the MOOSE framework: modifications to Moltres itself must be shared under LGPL, but proprietary code that links against Moltres as a library is permitted without disclosure. All three codes are free for academic, industrial, and government use without licensing fees, unlike commercial alternatives such as MCNP (proprietary, export-controlled, $5,000+ per license) or Serpent (free for non-commercial use only, commercial licenses negotiable).

### What hardware specification should I target for a dedicated simulation server?

For a small reactor physics group running assembly-level calculations, a dual-socket server with 64 CPU cores, 256 GB RAM, and 2 TB NVMe storage costs approximately $18,000-25,000. This handles full-core OpenMC calculations with 10 million particles per batch across 100 batches in 3-5 hours. The dominant cost driver is RAM capacity rather than core count—OpenMC's nuclear data library alone uses 25 GB, and large tally structures with fine energy groups can consume 50+ GB. For GPU-accelerated OpenMC with the experimental OpenCL backend, add an NVIDIA RTX 4090 or A-series GPU, but note that GPU support is still experimental and gains depend heavily on problem geometry.

### How do I handle nuclear data library management across multiple team members?

Centralize your nuclear data on a shared network filesystem or object store, then set the `OPENMC_CROSS_SECTIONS` environment variable in each user's environment or container to point to the same location. This ensures every team member uses identical cross sections, eliminating a common source of irreproducible results. Use environment modules or Docker bind mounts to enforce consistency. For NFS deployments, ensure the network has sufficient bandwidth (10 GbE minimum) because OpenMC streams HDF5 nuclear data during initialization—on slow networks, startup can take several minutes before the first particle history begins tracking.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Nuclear Engineering Simulation: OpenMC vs OpenMOC vs Moltres",
  "description": "Comprehensive comparison of OpenMC, OpenMOC, and Moltres for self-hosted nuclear reactor simulation. Compare Monte Carlo vs deterministic neutron transport with Docker Compose deployment and Python code examples.",
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
