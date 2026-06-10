---
title: "Self-Hosted Electromagnetic Simulation: MEEP vs openEMS vs gprMax"
date: "2026-06-10"
tags: ["electromagnetics", "simulation", "self-hosted", "fdtd", "engineering", "rf-design", "open-source", "computational-physics", "scientific-computing"]
draft: false
---

## Introduction

Electromagnetic (EM) simulation is essential for RF engineers, antenna designers, and photonics researchers. While commercial tools like CST Studio and Ansys HFSS dominate the industry, open-source alternatives have matured into capable, production-grade solvers. MEEP (MIT Electromagnetic Equation Propagation), openEMS, and gprMax represent three powerful self-hosted EM simulation frameworks — each targeting different application domains.

Deploying these solvers on a self-hosted workstation or server cluster gives you unlimited simulation capacity without per-core licensing fees. Whether you're designing a patch antenna, analyzing a photonic crystal, or modeling ground-penetrating radar, these FDTD-based solvers provide accurate results with Python scripting interfaces for automation and batch processing.

## Quick Comparison

| Feature | MEEP | openEMS | gprMax |
|---------|------|---------|--------|
| **Stars** | 1,672 | 677 | 847 |
| **Method** | FDTD + subpixel averaging | EC-FDTD (cylindrical) | FDTD (GPR-specific) |
| **Domain** | Photonics, metamaterials | RF circuits, antennas | Ground-penetrating radar |
| **Language** | C++ core, Python/ Scheme API | C++, Octave/Python API | Python + Cython |
| **Parallel** | MPI built-in | MPI via ParMetis | MPI + OpenMP |
| **Mesh** | Yee grid, subpixel | Hexahedral, cylindrical | Yee grid, PML |
| **Material Models** | Dispersive, nonlinear, gain | Isotropic, anisotropic | Debye, Drude, Lorentz |
| **Pre-built Docker** | No (conda/apt) | No (build from source) | No (pip install) |
| **Visualization** | h5utils, ParaView | ParaView, VTK | Built-in (plotly/matplotlib) |
| **License** | GPLv2 | GPLv3 | GPLv3 |

## Architecture and Solver Details

### MEEP: MIT's Photonics Workhorse

MEEP is the most widely adopted open-source EM solver, backed by decades of research at MIT. It uses a Yee-grid FDTD scheme with subpixel smoothing for accurate material interfaces — critical for photonic crystal simulations. MEEP supports dispersive materials via Lorentz-Drude models, nonlinear media, and even saturable gain for laser simulations:

```python
# MEEP: Photonic crystal band structure
import meep as mp

# Define a 2D photonic crystal
geometry = [mp.Cylinder(0.2, material=mp.Medium(epsilon=12))]
sources = [mp.Source(mp.GaussianSource(1.0, fwidth=0.1),
                     mp.Hz, mp.Vector3(0.2, 0))]

sim = mp.Simulation(cell_size=mp.Vector3(1, 1),
                    geometry=geometry,
                    sources=sources,
                    resolution=32)
sim.run(mp.at_every(1.0, mp.output_hfield_z), until=50)
```

### openEMS: RF and Antenna Design

openEMS uses the EC-FDTD (Electromagnetic Compatible FDTD) method with a hexahedral mesh — better suited for metallic structures and curved boundaries common in RF design. Its cylindrical mesh support is unique and ideal for coaxial cable modeling. Manufacturing-ready antenna designs can be simulated with sub-1% error compared to measurements:

```python
# openEMS: Patch antenna simulation
import openems
import numpy as np

FDTD = openems.OpenEMS()
FDTD.SetGaussExcite(2.4e9, 2.5e9)  # 2.4 GHz WiFi band

# Substrate
sub = FDTD.AddMaterial('substrate', epsilon=4.4)
FDTD.AddBox(sub, 0, [0, 0, 0], [60, 60, 1.6])

# Patch element  
FDTD.AddMetal('patch')
FDTD.AddBox('patch', 2, [10, 10, 1.6], [40, 40, 1.6])

FDTD.Run('patch_antenna', verbose=3)
```

### gprMax: Ground-Penetrating Radar Specialization

gprMax focuses exclusively on GPR simulation, modeling electromagnetic wave propagation through heterogeneous subsurface materials. It supports complex antenna models, dispersive soils, and realistic fracture geometries — making it the go-to tool for geophysical and civil engineering surveys:

```python
# gprMax: GPR survey simulation
import gprMax

# Soil with buried target
domain = gprMax.Domain(2.0, 2.0, 0.002)
soil = gprMax.Material(er=9.0, se=0.01, mr=1.0)
domain.add(soil)
# Metallic pipe target
pipe = gprMax.Cylinder(0.6, 1.0, 0.1, material='pec')
domain.add(pipe)
# Ricker wavelet source at 900 MHz
src = gprMax.HertzianDipole('z', 0.1, 1.0, 'ricker', 900e6)
domain.solve()
```

## Self-Hosted Deployment

While these tools don't ship with Docker Compose files, installing them in containerized environments ensures reproducibility. Here's a combined workstation setup:

```yaml
# docker-compose.yml — Scientific simulation workstation
version: '3.8'
services:
  meep:
    image: continuumio/miniconda3
    command: >
      bash -c "conda install -c conda-forge pymeep mpich -y &&
               python3 -c 'import meep; print(meep.__version__)' &&
               tail -f /dev/null"
    volumes:
      - ./simulations:/workspace
    restart: unless-stopped

  openems:
    build:
      context: ./openems-docker
      dockerfile: |
        FROM ubuntu:22.04
        RUN apt-get update && apt-get install -y \
            build-essential cmake libhdf5-dev \
            octave liboctave-dev parmetis \
            python3-numpy python3-matplotlib
        RUN git clone https://github.com/thliebig/openEMS.git && \
            cd openEMS && mkdir build && cd build && \
            cmake .. && make -j$(nproc) && make install
    volumes:
      - ./simulations:/workspace

  gprmax:
    image: python:3.11-slim
    command: >
      bash -c "pip install gprMax &&
               python3 -c 'import gprMax; print(gprMax.__version__)' &&
               tail -f /dev/null"
    volumes:
      - ./gpr-surveys:/workspace
```

For HPC environments, MPI parallelization scales across multiple nodes:

```bash
# MEEP MPI run across 4 nodes
mpirun -np 16 python3 broadband_absorber.py

# openEMS with MPI
mpirun -np 8 openEMS antenna_array.xml  

# gprMax with MPI + OpenMP threads
mpirun -np 4 python3 -m gprMax survey.in -n 8
```

## Why Self-Host Your EM Simulation Pipeline?

Commercial EM simulators charge $10,000-$50,000 per seat annually. A self-hosted open-source workstation gives you unlimited simulations for zero licensing cost — particularly valuable for startups, academic labs, and freelance RF engineers.

For context, our guide on [scientific simulation platforms](../2026-06-08-self-hosted-scientific-simulation-openfoam-elmer-calculix/) covers how OpenFOAM and CalculiX handle fluid dynamics and structural mechanics. Electromagnetic simulation completes the engineering simulation triad. If you're also working on [circuit-level simulation](../2026-06-08-self-hosted-spice-circuit-simulation-ngspice-qucs-xyce/), tools like ngspice complement EM solvers for end-to-end electronic design.

For managing large simulation datasets, our [scientific data management guide](../2026-06-09-self-hosted-scientific-data-management-irods-rucio-datalad-guide/) shows how iRODS and Rucio can version, catalog, and share your simulation results across teams. And when you need to visualize results, check out [scientific visualization tools](../2026-06-09-self-hosted-scientific-data-visualization-paraview-visit-vtkjs-pyvista/) like ParaView and VisIt.

## Model Validation and Verification Best Practices

Electromagnetic simulation results are only as good as the models they compute on. Without proper validation, simulation output can be misleading — particularly when mesh resolution is insufficient or boundary conditions are incorrectly applied. Following a systematic validation workflow ensures your self-hosted simulations produce results you can trust.

The golden rule of FDTD simulation: **at least 10-20 Yee cells per wavelength** at the highest frequency of interest. For a 5 GHz WiFi antenna, the free-space wavelength is 60 mm, requiring a maximum cell size of 3-6 mm. For photonic simulations at 500 THz (600 nm wavelength), cells must be 30-60 nm — a 10 µm domain needs 167-333 cells per dimension. Always run a convergence study: double the resolution and verify that S-parameters or resonance frequencies shift by less than 1%.

Boundary conditions are another common source of error. MEEP defaults to perfectly matched layers (PML), which absorb outgoing waves with minimal reflection. openEMS offers PML and Mur absorbing boundary options. gprMax uses PML by default. For antenna simulations where you need far-field patterns, ensure the PML is placed at least one wavelength from the radiating structure. Near-field to far-field (NFFF) transforms in MEEP and openEMS compute radiation patterns from near-field data recorded on a closed surface surrounding the antenna:

```python
# MEEP: Near-field to far-field transformation
nearfield_box = mp.Near2FarRegion(
    center=mp.Vector3(0, 0, 0),
    size=mp.Vector3(2, 2, 0),
    direction=mp.AUTOMATIC
)
sim.add_near2far(frq_cen, 0, 1, nearfield_box)
# After simulation, compute far fields
far_fields = sim.get_farfield(nearfield_box, mp.Vector3(1000, 0, 0))
```

Material parameter validation is critical, especially for dispersive media. When simulating soil with gprMax, verify your permittivity and conductivity values against published measurements for your soil type. Dry sand (εr=3-5), wet clay (εr=15-40), and freshwater (εr=80) produce dramatically different GPR signatures. openEMS supports importing S-parameter touchstone files (.s2p) for antenna matching networks — validate these against manufacturer datasheets.

For production workflows, implement automated regression testing: save reference results for a known geometry (a half-wave dipole or a simple dielectric slab), and re-run these test cases whenever you update your simulation environment or switch hardware. A 1% tolerance on S11 magnitude and phase ensures your toolchain remains consistent across machines and software versions.

## FAQ

### Which solver should I use for antenna design?

openEMS is your best choice. Its hexahedral mesh handles curved metallic structures accurately, and its EC-FDTD formulation is specifically designed for RF and antenna problems. The community maintains numerous antenna example scripts (patch, dipole, horn, Yagi-Uda).

### Can these tools handle GPU acceleration?

Currently, MEEP has experimental CUDA support via a development branch. openEMS supports OpenCL for some operations. gprMax uses OpenMP threading rather than GPU. For most simulations, CPU parallelization via MPI (MEEP, openEMS, gprMax all support MPI) is the primary scaling method. A 16-32 core workstation handles most practical simulations.

### What are the minimum hardware requirements?

A modern workstation with 32 GB RAM and 8+ cores can run useful simulations. Memory scales with domain size — a 200×200×200 Yee grid at double precision needs about 1 GB. For large 3D simulations (500+ cells per dimension), 64-128 GB RAM is recommended. All three solvers support checkpoint/restart for long-running jobs.

### How accurate are these open-source solvers compared to commercial tools?

For FDTD-based problems, MEEP and openEMS achieve accuracy within 1-3% of commercial tools (HFSS, CST) when used with proper mesh resolution — at least 10-20 cells per wavelength. MEEP's subpixel smoothing is particularly effective at reducing staircasing errors. The main gap versus commercial tools is in mesh generation (auto-adaptive meshing) and GUI-based post-processing.

### What's the best way to learn these tools?

Start with MEEP's excellent tutorial suite (Python examples covering photonic crystals, ring resonators, and mode calculations). openEMS provides antenna design tutorials from patch to horn antennas. gprMax's documentation includes real-world survey scenarios. All three support Python scripting, which lowers the learning curve compared to proprietary macro languages.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Electromagnetic Simulation: MEEP vs openEMS vs gprMax",
  "description": "Compare MEEP, openEMS, and gprMax for self-hosted electromagnetic simulation. Covers FDTD solvers, antenna design, GPR modeling, Docker deployment, and MPI parallelization.",
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
      "url": "https://pistack.xyz/logo.png"
    }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
