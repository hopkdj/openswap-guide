---
title: "Self-Hosted X-ray Absorption Spectroscopy Analysis: Demeter vs Larch vs xraylib for XANES & EXAFS"
date: "2026-06-13"
tags: ["x-ray-spectroscopy", "xanes", "exafs", "synchrotron", "materials-science", "spectroscopy", "open-source", "self-hosted"]
draft: false
---

X-ray Absorption Spectroscopy (XAS) is a powerful synchrotron-based technique used to probe the local atomic structure, oxidation state, and electronic configuration of materials. Unlike X-ray diffraction — which reveals long-range crystal structure — XAS is sensitive to the immediate environment (first few coordination shells) around a specific element. This makes it invaluable for studying catalysts, battery materials, amorphous solids, and biological metal centers.

A typical synchrotron beamtime produces gigabytes of raw data that must be reduced, normalized, and fitted to extract meaningful structural parameters. Self-hosting these analysis tools ensures data integrity between beamtimes and allows researchers to develop custom analysis protocols that persist across experiments.

In this guide, we compare three open-source frameworks for XAS analysis: **Demeter** (which includes Athena and Artemis), **Larch** (the modern successor to IFEFFIT), and **xraylib** (the fundamental cross-section library powering most XAS software).

## Understanding XAS Data: XANES and EXAFS

XAS spectra are divided into two regions with different physical information content:

- **XANES (X-ray Absorption Near-Edge Structure):** The region within ~50 eV of the absorption edge. Sensitive to oxidation state, coordination geometry, and electronic structure. XANES analysis is often qualitative — comparing spectra to reference compounds.
- **EXAFS (Extended X-ray Absorption Fine Structure):** The oscillatory region 50-1000 eV above the edge. Provides quantitative information: bond distances (±0.02 Å), coordination numbers, and Debye-Waller disorder factors. Requires fitting to theoretical scattering paths calculated by FEFF.

| Feature | Demeter (Athena/Artemis) | Larch | xraylib |
|---------|--------------------------|-------|---------|
| **Primary Function** | Data processing + EXAFS fitting | Full replacement for IFEFFIT | Cross-section calculations |
| **GitHub Stars** | 83 | 175 | 168 |
| **Language** | Perl (Athena), Fortran (IFEFFIT) | Python | C with Python bindings |
| **GUI** | Yes (Athena/Artemis) | Python scripting / Jupyter | Library (no GUI) |
| **FEFF Integration** | Built-in (Artemis) | Supported via feff6l | Input generation only |
| **Installation** | Windows/Mac GUI installers | pip, conda | pip, conda |
| **Key Strength** | Mature, beamline standard | Modern Python API, extensible | Low-level accuracy, speed |

## Demeter: The Beamline Standard

Demeter is a suite of Perl programs for XAS data processing and analysis, developed by Bruce Ravel at NIST. It includes **Athena** (data reduction, normalization, linear combination fitting) and **Artemis** (EXAFS fitting using FEFF). For over 15 years, Demeter has been the standard software at most synchrotron beamlines worldwide.

### Installation and Usage

Demeter is primarily distributed as Windows and macOS installer packages with bundled dependencies. On Linux, it can be built from source:

```bash
# Install system dependencies
sudo apt-get install libgfortran5 libgcc-s1 libx11-6

# Download Demeter package
wget https://github.com/bruceravel/demeter/archive/refs/tags/0.9.27.tar.gz
tar xzf 0.9.27.tar.gz && cd demeter-0.9.27

# Build IFEFFIT first, then Demeter
perl Build.PL
./Build
```

### Athena: Data Processing

Athena provides a graphical interface for importing beamline data files (in virtually any format), aligning multiple scans, performing energy calibration, background subtraction (AUTOBK algorithm), and normalization. Key features include:

```perl
# Typical Athena processing steps (GUI-driven):
# 1. Import raw mu(E) data from beamline file
# 2. Align reference foil for energy calibration
# 3. Deglitch — remove Bragg peaks from monochromator
# 4. Pre-edge subtraction + post-edge normalization
# 5. Convert E → k space, apply k-weight
# 6. Fourier transform to R-space
# 7. Export chi(k) for Artemis fitting
```

Athena's linear combination fitting (LCF) module is widely used for XANES analysis — fitting an unknown spectrum as a weighted sum of reference spectra to determine chemical speciation. The LCF module reports each reference's fractional contribution with uncertainty estimates.

### Artemis: EXAFS Fitting

Artemis uses FEFF-calculated scattering paths to fit EXAFS data. Users define a structural model (atomic positions, scattering paths), and Artemis refines parameters (bond distances, coordination numbers, sigma² disorder terms) by minimizing chi² between the theoretical and experimental chi(k):

```fortran
! Example Artemis input for fitting the first shell of Cu metal
! Parameter: amp = S02 amplitude (typically 0.7-1.0)
! Parameter: enot = energy shift (eV)
! Parameter: delr = change in Cu-Cu distance (Å)
! Parameter: ss = Debye-Waller factor (Å²)

guess amp = 0.85
guess enot = 3.0
guess delr = 0.0
guess ss = 0.003

path 1: Cu-Cu at 2.556 Å, N=12
  reff = 2.556
  delr = delr
  sigma2 = ss
```

## Larch: The Modern Python Alternative

Larch (X-ray Analysis Library) is a Python-based replacement for IFEFFIT, developed by Matt Newville at the University of Chicago. It provides a clean, modern API for XAS analysis that integrates naturally with the Python scientific ecosystem (NumPy, SciPy, Matplotlib).

### Installation

```bash
# Install via conda (recommended)
conda install -c conda-forge xraylarch

# Or via pip
pip install xraylarch

# Verify installation
larch -e "print('Larch version:', __version__)"
```

### Processing XAS Data with Larch

Larch's strength is its programmatic interface — ideal for batch processing hundreds of spectra from a beamtime run. Here's a complete processing workflow:

```python
from larch.io import read_ascii
from larch.xafs import pre_edge, autobk, xftf

# Read beamline data
dat = read_ascii("Cu_foil.dat")
dat.energy = dat.data[0]  # energy column
dat.mu     = dat.data[1]  # absorption column

# Pre-edge subtraction and normalization
pre_edge(dat, e0=8979.0, pre1=-150, pre2=-30, norm1=150, norm2=800)

# Background subtraction (AUTOBK)
autobk(dat, rbkg=1.0, kweight=2)

# Fourier transform
xftf(dat, kmin=2, kmax=14, dk=1, kweight=2)
```

### EXAFS Fitting with Larch

Larch integrates FEFF path calculations directly into its fitting engine:

```python
from larch.xafs import feffpath, feffit

# Define scattering paths from FEFF calculation
path1 = feffpath("feff0001.dat", label="Cu-Cu", degen=12,
                 s02="amp", delr="delr1", sigma2="ss1")

# Set up fit parameters
params = larch.Group(amp=0.85, enot=3.0, delr1=0.0, ss1=0.003)

# Perform fit
result = feffit(dat, [path1], params,
                kmin=2, kmax=14, kweight=2)
print(f"R-factor: {result.rfactor:.4f}")
print(f"Bond distance: {2.556 + params.delr1:.4f} Å")
```

Larch also supports advanced analysis methods including wavelet transform analysis, linear combination fitting, and principal component analysis of XANES spectra — all within the same Python session.

## xraylib: The Foundation Library

xraylib provides accurate calculations of X-ray fundamental parameters: cross-sections, fluorescence yields, line energies, and elastic/inelastic scattering factors. Most XAS analysis software (including Larch and Demeter) depends on xraylib or its predecessor for fundamental constants.

### Installation and Basic Usage

```bash
pip install xraylib
```

```python
import xraylib as xrl

# Get Fe K-edge energy
fe_k_edge = xrl.EdgeEnergy(26, xrl.K_SHELL)
print(f"Fe K-edge: {fe_k_edge:.1f} eV")  # 7112.0 eV

# Calculate photoabsorption cross-section at 10 keV
cs = xrl.CS_Total(26, 10.0)  # Iron at 10 keV
print(f"Total cross-section: {cs:.2f} cm²/g")

# Get fluorescence line energy
fe_ka1 = xrl.LineEnergy(26, xrl.KA1_LINE)
print(f"Fe Kα1: {fe_ka1:.1f} eV")  # 6403.8 eV

# Calculate mass attenuation coefficient
mac = xrl.CS_Photo(29, 8.047)  # Cu at Cu Kα
print(f"Photo cross-section: {mac:.2f} cm²/g")

# Get all subshell binding energies
for i in range(1, 30):
    energy = xrl.EdgeEnergy(26, xrl.K_SHELL + i - 1)
    if energy > 0:
        print(f"Shell {i}: {energy:.1f} eV")
```

xraylib's calculations are based on the EPDL97 and EADL evaluated data libraries from Lawrence Livermore National Laboratory, making it the gold standard for accuracy in X-ray physics computations.

## Setting Up a Self-Hosted XAS Analysis Server

For research groups with regular synchrotron access, deploying a dedicated analysis server with JupyterHub provides multi-user access to Larch, xraylib, and supporting tools:

```yaml
# docker-compose.yml
version: "3.8"
services:
  xas-analysis:
    image: jupyter/scipy-notebook:latest
    container_name: xas-server
    ports:
      - "8000:8888"
    volumes:
      - ./beamtime-data:/home/jovyan/data
      - ./feff-calculations:/home/jovyan/feff
    environment:
      - JUPYTER_ENABLE_LAB=yes
    command: >
      bash -c "pip install xraylarch xraylib pyshortcuts &&
               start-notebook.sh --NotebookApp.token=''"

  # Optional: shared storage for raw beamline data
  minio:
    image: minio/minio:latest
    container_name: beamtime-storage
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - ./minio-data:/data
    command: server /data --console-address :9001
```

## Data Pipeline from Beamline to Analysis

A typical synchrotron experiment workflow with self-hosted tools:

1. **Data Acquisition:** Raw data files (`.dat`, `.xdi`, `.hdf5`) saved to shared storage during beamtime
2. **Transfer & Backup:** Automated rsync from beamline workstation to institutional server after each scan
3. **Processing:** Athena (GUI) or Larch (scripted batch) for normalization and background subtraction
4. **EXAFS Fitting:** FEFF calculation → path definition → parameter refinement
5. **Visualization & Reporting:** Jupyter notebooks combining Larch results with Matplotlib/Plotly figures

## Why Self-Host Your XAS Analysis Pipeline?

Synchrotron beamtime is extraordinarily expensive and competitive — major facilities like APS, ESRF, and Spring-8 receive 3-5× more proposals than they can accommodate. Every allocated shift represents a year or more of preparation. Self-hosting your analysis pipeline provides three concrete benefits that protect this investment.

First, **data provenance tracking**: containerized tools with pinned versions create an immutable record of exactly how each dataset was processed. When a reviewer questions your EXAFS fitting procedure two years later, you can reproduce the analysis bit-for-bit by re-running the same container image. This is particularly important for XAS where normalization and background subtraction parameters (Rbkg, k-weight, Fourier transform range) significantly affect the fitted structural parameters.

Second, **batch processing at scale**: a single EXAFS beamtime can produce 200+ individual spectra from in-situ experiments (battery cycling, catalysis, high-pressure cells). Larch's Python API enables automated batch processing that would take days manually in Athena's GUI — fitting a dozen spectra takes minutes instead of hours.

Third, **FEFF calculation management**: FEFF is computationally expensive (hours per cluster for multiple-scattering paths). A dedicated server allows queueing calculations and caching results, avoiding redundant recomputation when fitting similar structures.

For crystallography and complementary structural methods, see our [guide to Phenix, CCP4 and XDS](../2026-06-11-self-hosted-crystallography-platforms-phenix-ccp4-xds/).
For other spectroscopic analysis tools, check our [comparison of HyperSpy, Quasar and RamanSPy](../2026-06-11-self-hosted-spectroscopic-analysis-hyperspy-quasar-ramanspy/).
For molecular visualization that complements XAS analysis, see our [MolStar, 3Dmol.js and NGLview guide](../2026-06-09-self-hosted-molecular-visualization-molstar-3dmoljs-nglview-ngl/).

## FAQ

### What's the difference between XANES and EXAFS?

XANES probes electronic structure (oxidation state, coordination geometry) within ~50 eV of the absorption edge. EXAFS probes local atomic structure (bond distances, coordination numbers) using oscillations extending 500-1000 eV past the edge.

### Do I need to install FEFF separately?

FEFF (version 6) is bundled with Larch as `feff6l`. For Demeter/Artemis, FEFF is also bundled. For advanced FEFF9/10 calculations (full multiple scattering, XANES simulation), you need a separate installation and license from the FEFF Project.

### Can Larch replace Athena entirely?

For most routine processing tasks, yes. Larch handles normalization, background subtraction, Fourier transforms, and EXAFS fitting. Athena's GUI remains preferred for interactive data exploration and quick quality checks during beamtime.

### Why does my EXAFS fit give unrealistic coordination numbers?

This typically indicates an incorrect S₀² (amplitude reduction factor). S₀² accounts for multi-electron excitations and should be determined from a reference compound measured under the same beamline conditions, then fixed during fitting of unknown samples.

### How do I handle self-absorption effects in fluorescence-mode XAS?

For concentrated samples measured in fluorescence mode, self-absorption attenuates the EXAFS amplitude. Both Athena and Larch provide self-absorption correction algorithms. For thin, dilute samples (Δμx < 1), the correction is negligible.

### Is xraylib suitable for simulating XAS spectra?

No — xraylib calculates atomic cross-sections and fundamental parameters, not spectral shapes. For XANES simulation, use FEFF (full multiple scattering), FDMNES (finite difference method), or ORCA/Quantum ESPRESSO (DFT-based).

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted X-ray Absorption Spectroscopy Analysis: Demeter vs Larch vs xraylib for XANES & EXAFS",
  "description": "Compare Demeter (Athena/Artemis), Larch, and xraylib for self-hosted XAS analysis. Covers XANES processing, EXAFS fitting with FEFF, cross-section calculations, and Docker deployment for synchrotron data.",
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
