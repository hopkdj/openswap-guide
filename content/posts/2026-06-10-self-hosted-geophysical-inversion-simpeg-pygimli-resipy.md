---
title: "Self-Hosted Geophysical Inversion & Subsurface Modeling: SimPEG vs pyGIMLI vs ResIPy"
date: "2026-06-10"
tags: ["geophysics", "inversion", "self-hosted", "subsurface-modeling", "electrical-resistivity", "scientific-computing", "open-source", "geology", "groundwater"]
draft: false
---

## Introduction

Geophysical inversion transforms raw field measurements — electrical resistivity, gravity, magnetics — into interpretable subsurface models. This is the computational backbone of groundwater exploration, mineral prospecting, and environmental site characterization. While commercial packages like Res2DInv and Oasis Montaj charge per-survey licensing, the open-source ecosystem now offers production-grade alternatives: SimPEG, pyGIMLI, and ResIPy.

These Python-based frameworks leverage modern optimization algorithms and high-performance computing to solve inverse problems that would have required supercomputers a decade ago. Deploying them on a self-hosted workstation gives geophysicists unlimited modeling capacity — process as many survey lines as needed without worrying about license counts or seat availability.

## Quick Comparison

| Feature | SimPEG | pyGIMLI | ResIPy |
|---------|--------|---------|--------|
| **Stars** | 654 | 487 | 40 |
| **Core Language** | Python + Cython | C++ core, Python bindings | Python GUI + API |
| **Methods** | DC/IP, EM, gravity, magnetics, flow | ERT, SIP, MRS, traveltime | DC resistivity, IP |
| **Mesh** | Tensor, tree, octree, unstructured | Triangle, TetGen 2D/3D | 2D quadrilateral |
| **Inversion** | Tikhonov, sparse, joint | Gauss-Newton, L-BFGS | L1/L2, time-lapse |
| **Parallel** | Multiprocessing | OpenMP (C++ core) | Single process |
| **GUI** | Jupyter-based | pyGIMLi viewer | Qt5 desktop GUI |
| **File Formats** | UBC, VTK, h5 | BERT, unified format | R2 format, Res2DInv |
| **Pre-built Docker** | No (conda/pip) | No (conda) | No (GitLab mirror) |
| **License** | MIT | Apache 2.0 | GPLv3 |

## Architecture and Inversion Workflows

### SimPEG: The General-Purpose Geophysical Framework

SimPEG (Simulation and Parameter Estimation in Geophysics) takes a modular, equation-oriented approach. You define the physics (DC resistivity, induced polarization, electromagnetics, gravity, magnetics, or fluid flow), the regularization, and the optimization separately — then compose them into an inversion. This makes it the most flexible framework for research and custom workflows:

```python
# SimPEG: 2D DC resistivity inversion
import SimPEG
from SimPEG import maps, data, regularization, optimization, inversion, inverse_problem
from SimPEG.electromagnetics import resistivity as dc
import discretize
import numpy as np

# Build mesh and survey
mesh = discretize.TensorMesh([[(1, 30)], [(1, 20)]], x0="CN")
survey = dc.survey.Survey(dc.sources.Dipole(...))

# Forward simulation
simulation = dc.simulation_2d.Simulation2DNodal(
    mesh, survey.survey_type='dipole-dipole', rhoMap=maps.ExpMap(mesh)
)

# Inversion with Tikhonov regularization
reg = regularization.Tikhonov(mesh)
opt = optimization.InexactGaussNewton(maxIter=10)
inv = inversion.BaseInversion(
    inverse_problem.BaseInvProblem(simulation, reg, opt)
)
recovered_model = inv.run(dobs_survey)
```

### pyGIMLI: Geophysics with a C++ Engine

pyGIMLI (Geophysical Inversion and Modeling Library) provides a unified C++ backend with Python bindings. Unlike SimPEG's pure-Python approach, pyGIMLI's computationally intensive operations run in compiled C++, giving it a performance edge for large 3D surveys. It supports ERT (electrical resistivity tomography), SIP (spectral induced polarization), and traveltime tomography with a consistent API:

```python
# pyGIMLI: ERT cross-borehole inversion
import pygimli as pg
from pygimli.physics import ert

# Load field data and define geometry
data = ert.load('crosshole_data.dat')
mgr = ert.ERTManager(data)

# Invert with structural constraints
model = mgr.invert(
    lam=20,          # regularization strength
    zWeight=0.3,     # vertical smoothness
    verbose=True     
)

# Export for visualization
mgr.showResult()
pg.meshtools.exportVTK(mgr.paraDomain, model, 'result.vtk')
```

### ResIPy: Field-Ready ERT Processing

ResIPy is the most field-oriented of the three, built specifically for ERT/IP data processing with a Qt5 graphical interface. Based on the well-validated R2 and cR2 inversion codes, it handles standard resistivity surveys with minimal configuration — ideal for consulting geophysicists who need reliable results without writing code:

```python
# ResIPy API: Automated ERT processing
from resipy import Project

proj = Project(typ='R2')
proj.createSurvey('survey.dat', ftype='Protocol')
proj.filterUnpaired()
proj.filterReciprocals(threshold=5.0)  # 5% reciprocity check

# Invert with robust (L1) data misfit
proj.invert(
    reg='l1', 
    dmod='l1',  
    istart=3,   
    isave=1     
)
proj.showResults()
```

## Self-Hosted Deployment

All three frameworks install via conda or pip. A reproducible workstation setup ensures consistent environments across team members:

```bash
#!/bin/bash
# Geophysical inversion workstation setup

# SimPEG
conda create -n simpeg python=3.11 -y
conda activate simpeg
conda install -c conda-forge simpeg discretize pymatsolver -y

# pyGIMLI
conda create -n pygimli python=3.11 -y
conda activate pygimli
conda install -c gimli -c conda-forge pygimli -y

# ResIPy (from GitLab mirror)
conda create -n resipy python=3.10 -y
conda activate resipy
pip install git+https://gitlab.com/hkex/resipy.git
```

For Docker deployment:

```yaml
# docker-compose.yml — Geophysical inversion server
version: '3.8'
services:
  simpeg:
    image: condaforge/miniforge3
    command: >
      bash -c "conda install -c conda-forge simpeg discretize -y &&
               jupyter lab --ip=0.0.0.0 --port=8888 --allow-root"
    ports:
      - "8888:8888"
    volumes:
      - ./surveys:/data
      - ./notebooks:/home/jovyan

  pygimli:
    image: condaforge/miniforge3
    command: >
      bash -c "conda install -c gimli -c conda-forge pygimli -y &&
               tail -f /dev/null"
    volumes:
      - ./surveys:/data
```

## Why Self-Host Your Geophysical Inversion Pipeline?

Commercial geophysical software licensing is notoriously expensive — annual subscriptions for a single module often exceed $10,000 USD. For small consultancies and academic research groups, self-hosting SimPEG or pyGIMLI eliminates per-survey costs entirely. You pay for hardware once and run unlimited inversions.

As covered in our [scientific simulation platforms guide](../2026-06-08-self-hosted-scientific-simulation-openfoam-elmer-calculix/), open-source computational tools have reached parity with commercial alternatives for many engineering and scientific workflows. Geophysical inversion is no exception — the codes underlying SimPEG and pyGIMLI have been validated against benchmarks and field data from major research programs worldwide.

For managing the large datasets that inversion produces, our [scientific data management guide](../2026-06-09-self-hosted-scientific-data-management-irods-rucio-datalad-guide/) covers iRODS and DataLad for versioning and sharing inversion results. When you need to visualize 3D resistivity models, tools like [ParaView and VisIt](../2026-06-09-self-hosted-scientific-data-visualization-paraview-visit-vtkjs-pyvista/) render interactive volumetric views of the subsurface.

And for those working at the intersection of geophysics and agent-based simulation, our [agent-based modeling guide](../2026-06-10-self-hosted-agent-based-modeling-netlogo-gama-repast/) demonstrates how groundwater models can feed into land-use change simulations.

## Handling Real-World Geophysical Data Challenges

Field geophysical data rarely matches the clean, noise-free datasets used in tutorials. Real electrode arrays encounter contact resistance problems, telluric noise, cultural interference from power lines, and topographic variations that must be corrected before inversion can produce meaningful results. Understanding these real-world challenges and how to address them in SimPEG, pyGIMLI, and ResIPy is essential for producing geologically plausible models.

Electrode contact resistance is the most common field problem. When an electrode doesn't make good contact with the ground — common in dry sand, gravel, or frozen soil — the measured potentials become unreliable. Before inversion, filter your dataset for contact resistance issues. ResIPy provides a dedicated UI for this: electrodes with resistance exceeding configurable thresholds (typically 2-5 kOhm for standard stainless steel stakes) are flagged. SimPEG and pyGIMLI offer programmatic filtering:

```python
# pyGIMLI: Filter by electrode contact resistance
import pygimli as pg
data = pg.DataContainerERT('field_data.dat')
data = data.filter(data('r') < 5000)  # Remove readings > 5 kOhm
data = data.filter(data('rhoa') > 0)  # Remove negative apparent resistivity
```

Topography correction is equally important. A 10-meter hill on a 50-meter survey line shifts apparent resistivity values by 5-15%, potentially creating false anomalies. All three frameworks support topography incorporation. SimPEG can import digital elevation models (DEMs) to deform the inversion mesh. pyGIMLI's `ert.ERTManager` includes automatic topography handling when electrode elevations are specified. For ResIPy, import a `.topo` file with x-z coordinates for each electrode position.

Temporal noise from telluric currents and cultural interference (50/60 Hz power line harmonics) requires stacking and filtering. Acquire multiple readings per quadrupole and compute the coefficient of variation — reject readings with >3% variation. For time-domain IP surveys, apply a 50/60 Hz notch filter before decay curve analysis:

```python
# SimPEG: Apply notch filter for power line noise
from scipy import signal
import numpy as np

def notch_filter(data, fs, freq, Q=30):
    b, a = signal.iirnotch(freq, Q, fs)
    return signal.filtfilt(b, a, data)

fs = 10  # sampling frequency (Hz)
filtered = notch_filter(raw_vp, fs, freq=50, Q=30)
```

When working with legacy datasets from different instruments, coordinate system and unit conversion become critical. Some resistivity meters output in ohm-meters, others in millivolts/amp. Some GPS units provide UTM coordinates while others use latitude/longitude. Always normalize your data to a consistent coordinate reference system (WGS84 UTM is the de facto standard for near-surface geophysics) and verify that units match across your entire processing pipeline before starting the inversion.

## FAQ

### Which framework should I use for production ERT surveys?

For standard 2D ERT surveys with minimal coding, ResIPy provides a familiar GUI workflow similar to Res2DInv. For advanced processing (3D, time-lapse, spectral IP), pyGIMLI offers the best performance due to its C++ backend. For research and custom physics, SimPEG's modular architecture is ideal.

### How does the inversion accuracy compare to commercial software?

SimPEG and pyGIMLI use the same numerical methods (finite volume, Gauss-Newton optimization) as commercial packages like Res2DInv and AarhusInv. Benchmarks show agreement within 1-2% for standard ERT surveys. ResIPy specifically wraps the R2 code — the same forward/inversion engine used in academic research for 20+ years.

### What hardware do I need for 3D inversions?

A 3D ERT survey with 50,000 data points and a 100,000-cell mesh requires about 16-32 GB RAM and completes in 1-2 hours on a modern 8-core workstation. Very large surveys (1M+ cells) benefit from 64 GB RAM. GPU acceleration is limited — CPU parallelization via multiprocessing (SimPEG) or OpenMP (pyGIMLI) is the primary approach.

### Can I process magnetotelluric (MT) or seismic data with these tools?

SimPEG supports MT forward modeling and inversion (1D and 2D). Seismic inversion is not a primary focus of these three frameworks — pyGIMLI has experimental traveltime tomography, but for full-waveform seismic inversion, you would complement these with tools like Madagascar or Seismic Unix.

### How do I handle data quality control before inversion?

All three tools provide reciprocity checking, data filtering, and pseudo-section visualization. ResIPy excels at this with its GUI-based quality control pipeline — filter by reciprocity error, remove noisy quadrupoles, and visualize pseudo-sections before inversion. SimPEG and pyGIMLI offer the same through their Python APIs for automated batch processing.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Geophysical Inversion & Subsurface Modeling: SimPEG vs pyGIMLI vs ResIPy",
  "description": "Compare SimPEG, pyGIMLI, and ResIPy for self-hosted geophysical inversion. Covers DC resistivity, ERT processing, Docker deployment, and Python inversion workflows for groundwater and mineral exploration.",
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
