---
title: "Self-Hosted Flow Cytometry Data Analysis: FlowKit vs CytoFlow vs pytometry"
date: "2026-06-13"
tags: ["flow-cytometry", "bioinformatics", "data-analysis", "python", "scientific-computing", "biomedical-research"]
draft: false
---

## Introduction

Flow cytometry is a cornerstone technique in biomedical research, immunology, and clinical diagnostics. A single experiment can generate data for millions of individual cells, each measured across dozens of parameters. While commercial packages like FlowJo dominate many labs, the open-source ecosystem has matured dramatically — offering reproducible, scriptable, and self-hosted analysis pipelines that can be deployed on lab servers, HPC clusters, or cloud instances.

This guide compares four leading open-source frameworks for flow cytometry data analysis: **FlowKit**, **CytoFlow**, **pytometry**, and **FlowCal**. Each takes a different approach to the same core problem: turning raw `.fcs` files into biologically meaningful insights.

## Tool Overview

| Tool | Language | Stars | Approach | Best For |
|------|----------|-------|----------|----------|
| FlowKit | Python | 216+ | GatingML-compatible, FlowJo parity | Lab pipelines replacing commercial software |
| CytoFlow | Python | 217+ | Bayesian statistics, reproducible workflows | Quantitative, statistics-heavy experiments |
| pytometry | Python | 60+ | scverse ecosystem integration | Single-cell multi-omics integration |
| FlowCal | Python | 56+ | Calibration-focused, Excel output | Instrument QC and calibration curves |

### FlowKit

FlowKit is designed as a direct open-source alternative to FlowJo, supporting GatingML — the ISAC standard for sharing gating strategies. It can read FlowJo workspaces (`.wsp` files), transform data with logicle/biexponential scaling, and export results as GatingML for cross-platform reproducibility.

Key capabilities:
- Full GatingML 2.0 import and export
- Logicle (biexponential), arcsinh, and log transformations
- Compensation matrix application
- Dimensionality reduction via PCA and t-SNE
- FlowJo workspace (`.wsp`) compatibility

### CytoFlow

Where FlowKit emphasizes FlowJo compatibility, CytoFlow takes a statistics-first approach. It uses Bayesian hierarchical models, mixture modeling, and modern Python data science tooling (pandas, scikit-learn) to extract quantitative insights. CytoFlow is ideal for experiments where you need rigorous statistical comparisons between sample groups.

Key capabilities:
- Bayesian Gaussian mixture models for automated gating
- Statistical testing between populations
- Integration with scikit-learn pipelines
- Reproducible Jupyter notebook workflows
- Built-in visualization with matplotlib and seaborn

### pytometry

pytometry is part of the scverse ecosystem — the same family that includes Scanpy (single-cell RNA-seq) and Squidpy (spatial omics). It brings flow and mass cytometry data into the same analysis framework used for single-cell genomics, enabling true multi-modal integration. If you're already using Scanpy for scRNA-seq, pytometry lets you analyze flow data with the same AnnData objects.

Key capabilities:
- Read `.fcs` files directly into AnnData objects
- Seamless integration with Scanpy, scvi-tools
- Standard preprocessing: compensation, transformation, normalization
- Compatible with the broader scverse single-cell ecosystem
- Support for mass cytometry (CyTOF) data

### FlowCal

FlowCal focuses on a specific but critical workflow: instrument calibration and quality control. It reads calibration bead data, fits standard curves, and converts arbitrary fluorescence units to calibrated Molecules of Equivalent Soluble Fluorochrome (MESF). For core facilities and labs running multi-instrument experiments, FlowCal ensures cross-instrument comparability.

Key capabilities:
- MESF bead calibration with standard curve fitting
- Excel-based reporting for lab notebooks
- Batch processing of calibration runs
- Instrument QC tracking over time
- Conversion of fluorescence to standardized units

## Installation and Setup

All four tools can be installed via pip and deployed on a shared lab server, headless workstation, or JupyterHub instance for multi-user access.

```bash
# Create a shared analysis environment
python3 -m venv /opt/cytometry-env
source /opt/cytometry-env/bin/activate

# Install all four frameworks
pip install flowkit cytoflow pytometry FlowCal

# For JupyterHub multi-user deployment
pip install jupyterhub jupyterlab
```

For Docker-based deployment on a lab server, create a JupyterHub stack with all tools pre-installed:

```yaml
# docker-compose.yml for cytometry analysis server
version: "3.8"
services:
  jupyterhub:
    image: jupyterhub/jupyterhub:latest
    ports:
      - "8000:8000"
    volumes:
      - ./jupyterhub_config.py:/srv/jupyterhub/jupyterhub_config.py
      - /data/cytometry:/data
    environment:
      - DOCKER_JUPYTER_IMAGE=jupyter/scipy-notebook:latest

  singleuser:
    image: jupyter/scipy-notebook:latest
    command: |
      pip install flowkit cytoflow pytometry FlowCal
```

## Comparison Table: Feature Matrix

| Feature | FlowKit | CytoFlow | pytometry | FlowCal |
|---------|---------|----------|-----------|---------|
| GatingML support | Full import/export | No | No | No |
| FlowJo workspace import | Yes | No | No | No |
| Automated gating | Via sklearn | Bayesian mixture models | Via Scanpy | No |
| Dimensionality reduction | PCA, t-SNE | PCA, t-SNE | PCA, t-SNE, UMAP | No |
| AnnData integration | Limited | No | Native | No |
| MESF calibration | No | No | No | Yes |
| Statistical testing | Basic | Advanced (Bayesian) | Via scipy | No |
| Batch processing | Yes | Yes | Yes | Yes |
| Excel export | Via pandas | Via pandas | Via pandas | Native |
| scverse ecosystem | No | No | Yes | No |
| License | BSD-3 | BSD-3 | BSD-3 | BSD-3 |

## Choosing the Right Tool

### For Core Facilities
FlowKit + FlowCal together form a complete open-source pipeline. FlowKit handles the gating and analysis while FlowCal handles instrument QC. This combination can replace a commercial FlowJo license for most routine workflows, with the added benefit of GatingML export for publication-ready method sharing.

### For Quantitative Immunology
CytoFlow's Bayesian models provide uncertainty quantification that frequentist methods can't match. When you need to report confidence intervals on population frequencies or test whether a treatment shifts a population distribution, CytoFlow's statistical framework is the strongest option.

### For Multi-Omics Labs
If your lab does both flow cytometry and single-cell RNA-seq, pytometry's AnnData integration is transformative. You can analyze flow data and scRNA-seq data in the same Python session, using the same preprocessing and visualization code. This dramatically reduces the context-switching overhead between platforms.

For related reading: For related bioimaging workflows, see our [microscope image analysis guide](../2026-06-09-self-hosted-microscope-image-analysis-qupath-imagej-cellprofiler/). If you're setting up a digital pathology pipeline, our [digital pathology platform comparison](../2026-06-11-self-hosted-digital-pathology-omero-dsa-camicroscope/) covers complementary tools. For instrument control and data acquisition, our [electronics lab software guide](../2026-06-09-self-hosted-electronics-lab-software-sigrok-scopy-eez-studio/) covers hardware interfacing.

## Why Self-Host Flow Cytometry Analysis?

Running flow cytometry analysis on your own infrastructure offers substantial advantages. Commercial packages like FlowJo charge per-seat licenses that scale poorly for growing labs — a 10-person lab can easily spend $5,000-$10,000 annually. Self-hosted open-source alternatives eliminate these recurring costs entirely.

Data sovereignty is equally important. Flow cytometry data often contains protected health information (PHI) from clinical trials or patient samples. Running analysis on lab-owned servers keeps sensitive data within institutional firewalls, satisfying IRB and HIPAA requirements without complex data-use agreements with cloud providers.

Reproducibility is the third pillar. GatingML exports from FlowKit produce machine-readable gating strategies that can be archived alongside publications. Unlike screenshots of FlowJo gates, GatingML files can be re-executed by reviewers or future lab members, ensuring your analysis is truly reproducible. The combination of scripted analysis (Jupyter notebooks) and standardized gating formats (GatingML) creates an audit trail that manual GUI-based workflows cannot match.

For labs already running computational infrastructure, adding a cytometry analysis server is straightforward. A modest server with 32 GB RAM can handle most panel sizes, and the same machine can serve multiple users via JupyterHub. For labs working with mass cytometry (CyTOF) or spectral flow data, pytometry's efficient AnnData backend handles the larger data volumes without requiring GPU acceleration.

## FAQ

### Can these tools read `.fcs` 3.0 and 3.1 files?
Yes. Both FlowKit and pytometry support FCS 3.0 and 3.1 formats, including spectral flow data from Cytek instruments. FlowKit uses the `fcsparser` backend which handles most instrument vendors' FCS variants. If you encounter a non-standard FCS file, pytometry's AnnData-based parser is often more forgiving.

### How does automated gating compare to manual gating?
Automated gating via CytoFlow's Bayesian mixture models achieves >90% concordance with expert manual gating for standard lymphocyte populations (CD4+, CD8+, CD19+). However, for rare populations (<0.1%) or non-standard markers, manual review is still recommended. The best workflow uses automated gating as a first pass, followed by manual refinement of ambiguous populations in FlowKit.

### Can I integrate this with an existing LIMS?
Yes. FlowKit and pytometry both support programmatic data loading from network filesystems and databases. A typical integration with SENAITE or Bika LIMS involves a watcher script that detects new `.fcs` files, runs a pre-configured analysis pipeline, and pushes results back to the LIMS via REST API. For core facilities with high throughput, this eliminates the manual "download from instrument, open in FlowJo, gate, export" cycle.

### Do I need a GPU for these tools?
No. Flow cytometry data analysis is CPU-bound and works well on standard server hardware. For a typical 12-color panel with 1 million events, analysis takes 10-30 seconds on a modern CPU. Even mass cytometry (40+ parameters) runs efficiently on CPU. The only exception is if you're running deep learning-based cell classification models, in which case a single GPU can accelerate training.

### How do I share gating strategies with collaborators who use FlowJo?
FlowKit can import FlowJo `.wsp` workspaces, apply the gating hierarchy, and export the results as GatingML. Collaborators using FlowJo can also import GatingML files generated by FlowKit. This bidirectional compatibility means open-source and commercial users can collaborate on the same gating strategy. For publication, export the GatingML alongside your manuscript to satisfy journal data-sharing requirements.

### What about spectral flow cytometry?
Spectral flow data (from Cytek Aurora instruments) is supported by both FlowKit and pytometry. The unmixing step — converting raw detector signals to fluorochrome abundances — is typically performed by the instrument software. Post-unmixing, the compensated FCS files can be analyzed with any of these tools. For custom unmixing algorithms, CytoFlow's statistical framework can be extended with user-defined unmixing matrices.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Flow Cytometry Data Analysis: FlowKit vs CytoFlow vs pytometry",
  "description": "Compare open-source flow cytometry analysis platforms: FlowKit for GatingML compatibility, CytoFlow for Bayesian statistics, pytometry for single-cell multi-omics integration, and FlowCal for instrument calibration. Self-hosted deployment guide included.",
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

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
