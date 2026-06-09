---
title: "Self-Hosted Mass Spectrometry & Proteomics Analysis: OpenMS vs ProteoWizard vs MZmine"
date: "2026-06-09"
tags: ["mass-spectrometry", "proteomics", "bioinformatics", "scientific-computing", "metabolomics", "open-science"]
draft: false
---

## Introduction

Mass spectrometry (MS) generates enormous datasets — a single proteomics experiment can produce tens of gigabytes of raw spectral data. Processing this data into biological insights requires specialized computational tools. Running these tools on your own infrastructure preserves data ownership, allows custom pipeline development, and eliminates recurring cloud costs.

This article compares three open-source platforms for self-hosted mass spectrometry data analysis: **OpenMS**, **ProteoWizard**, and **MZmine 3**. Each serves different niches within the MS analysis ecosystem.

| Feature | OpenMS | ProteoWizard | MZmine 3 |
|---------|--------|-------------|----------|
| **Stars** | 598+ | 305+ | 277+ |
| **Primary Focus** | Proteomics workflow engine | Data format conversion | Metabolomics & lipidomics |
| **Language** | C++ / Python | C++ / C# | Java |
| **GUI Available** | Yes (TOPPAS/TOPPView) | Yes (SeeMS) | Yes |
| **Last Updated** | 2026-06 | 2026-06 | 2026-06 |
| **Pipeline Automation** | TOPPAS workflow editor | msconvert CLI | Batch processing |
| **Key Strength** | Complete proteomics pipeline | Universal format converter | Metabolomics feature detection |
| **Docker Support** | Yes (Biocontainers) | Yes (Biocontainers) | Yes |

## OpenMS: The Complete Proteomics Platform

OpenMS provides an end-to-end solution for proteomics data analysis, from raw file reading to statistical evaluation. With over 180 tools in its TOPP (The OpenMS Proteomics Pipeline) suite, it covers peptide identification, quantification, and data visualization.

**Deploying OpenMS with Docker:**

```yaml
version: "3.8"
services:
  openms:
    image: biocontainers/openms:3.0.0
    container_name: openms-server
    volumes:
      - ./raw_data:/data/raw:ro
      - ./results:/data/results
      - ./databases:/data/databases:ro
    working_dir: /data
    command: >
      bash -c "
      PeakPickerHiRes -in /data/raw/sample.mzML -out /data/results/peaks.mzML &&
      FeatureFinderMetabo -in /data/results/peaks.mzML -out /data/results/features.featureXML
      "
    deploy:
      resources:
        limits:
          memory: 32G
          cpus: '16'
```

**Building a custom proteomics pipeline:**

```python
#!/usr/bin/env python3
"""Automated proteomics pipeline using OpenMS pyOpenMS."""
import pyopenms as oms
import glob, os

# Load raw mass spec data
raw_files = glob.glob("/data/raw/*.mzML")
for raw_file in raw_files:
    exp = oms.MSExperiment()
    oms.MzMLFile().load(raw_file, exp)
    
    # Peak picking
    peak_picker = oms.PeakPickerHiRes()
    peak_picker.pickExperiment(exp)
    
    # Feature detection
    ff = oms.FeatureFinder()
    ff.run("centroided", exp, oms.FeatureMap(), oms.Param(), oms.FeatureFindingMetabo())
    
    print(f"Processed {raw_file}: {exp.size()} spectra")
```

OpenMS's TOPPAS workflow editor enables drag-and-drop pipeline construction, making it accessible to researchers without programming experience. The pyOpenMS Python bindings allow programmatic access for automation in self-hosted environments.

## ProteoWizard: The Universal Translator

ProteoWizard is the Swiss Army knife of mass spectrometry data formats. Its primary tool, **msconvert**, converts between virtually all vendor-specific MS formats (Thermo .raw, Bruker .d, Waters .raw, AB Sciex .wiff) and open standards (mzML, mzXML, MGF).

```bash
# Install via conda
conda create -n pwiz -c bioconda proteowizard
conda activate pwiz

# Convert Thermo .raw to open mzML format
msconvert sample.raw --mzML --32 --zlib   --filter "peakPicking true 1-"   --outdir /data/converted/
```

**Self-hosted conversion server with Docker:**

```yaml
services:
  msconvert:
    image: chambm/pwiz-skyline-i-agree-to-the-vendor-licenses:latest
    container_name: msconvert-server
    volumes:
      - ./raw_data:/data/raw:ro
      - ./converted:/data/converted
    working_dir: /data
    command: >
      bash -c "
      for f in /data/raw/*.raw; do
        wine msconvert $$f --mzML --outdir /data/converted/ --filter 'peakPicking true 1-'
      done
      "
```

ProteoWizard also includes SeeMS for interactive data visualization and Skyline integration for targeted proteomics. For labs that receive data from multiple instrument vendors, it's the essential first step in any analysis pipeline.

## MZmine 3: Metabolomics Specialist

MZmine 3 focuses on small molecule analysis — metabolomics, lipidomics, and natural products discovery. Its feature detection algorithms are optimized for LC-MS and GC-MS data, with specialized modules for isotope pattern detection, adduct identification, and molecular networking.

```bash
# Deploy MZmine 3 with Docker
docker run -d   --name mzmine-server   -v /data/raw:/data/raw:ro   -v /data/results:/data/results   -e MZMINE_MEMORY=32G   mzmine/mzmine3:latest   batch   --input /data/raw/sample.mzML   --output /data/results/sample_features.csv   --parameters /data/params.xml
```

**Automated batch processing configuration:**

```xml
<?xml version="1.0"?>
<batch>
  <batchstep method="io.github.mzmine.modules.io.import_rawdata_all.AllSpectralDataImportModule">
    <parameter name="File names">
      <file>/data/raw/sample.mzML</file>
    </parameter>
  </batchstep>
  <batchstep method="io.github.mzmine.modules.dataprocessing.featdet_massdetection.MassDetectionModule">
    <parameter name="Mass detector">centroid</parameter>
    <parameter name="Noise level">1E3</parameter>
  </batchstep>
  <batchstep method="io.github.mzmine.modules.dataprocessing.featdet_chromatogrambuilder.ChromatogramBuilderModule">
    <parameter name="Minimum time span (min)">0.05</parameter>
    <parameter name="Minimum height">3E3</parameter>
  </batchstep>
</batch>
```

MZmine 3 excels at GNPS-compatible molecular networking, feature-based molecular networking (FBMN), and Ion Identity Molecular Networking (IIMN). These techniques connect related molecules across samples based on MS/MS spectral similarity.

## Deployment Architecture

All three tools can be integrated into a self-hosted scientific data platform:

```
┌─────────────────────────────────────────────┐
│              Self-Hosted MS Platform          │
│                                               │
│  ┌───────────┐  ┌──────────┐  ┌──────────┐  │
│  │ OpenMS    │  │ Proteo-  │  │ MZmine 3 │  │
│  │ Pipeline  │  │ Wizard   │  │ Batch    │  │
│  │ Server    │  │ Converter│  │ Server   │  │
│  └─────┬─────┘  └────┬─────┘  └────┬─────┘  │
│        │              │              │        │
│  ┌─────┴──────────────┴──────────────┴─────┐  │
│  │        Shared Storage (NFS/Gluster)      │  │
│  │   /raw → /converted → /features → /db   │  │
│  └─────────────────────────────────────────┘  │
│                                               │
│  ┌──────────────────────────────────────┐    │
│  │    Web UI (Galaxy / custom Flask)     │    │
│  └──────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

## Why Self-Host Your Mass Spectrometry Analysis?

Mass spectrometry data is frequently subject to intellectual property restrictions — pharmaceutical companies, clinical labs, and academic consortia cannot upload proprietary data to cloud services. Self-hosted analysis keeps sensitive spectral data behind your firewall while still enabling collaborative science through controlled data sharing.

For managing your processed datasets, see our [scientific data management guide](../2026-06-09-self-hosted-scientific-data-management-irods-rucio-datalad-guide/). When you need to create publication-quality figures from your results, our [scientific visualization guide](../2026-06-09-self-hosted-scientific-data-visualization-paraview-visit-vtkjs-pyvista/) covers open-source tools for rendering spectral and chromatographic data.

**Reproducibility** is a major concern in computational proteomics. By containerizing your analysis pipelines with Docker and versioning your parameter files in Git, you create fully reproducible workflows that can be shared with collaborators or reviewers. This approach has been adopted by major proteomics journals and is becoming a requirement for publication.

**Scalability** is another key factor — a single Thermo Orbitrap can generate 50+ GB per day. Cloud processing at this volume becomes expensive quickly, while a local server with 128 GB RAM and 32 cores can process a full day's data overnight with zero per-sample costs.

## Integrating Mass Spectrometry with Laboratory Data Systems

Processing mass spectrometry data in isolation limits its value. Integrating your self-hosted MS pipeline with broader laboratory informatics creates a cohesive research data ecosystem.

**Connecting to ELN systems**: Electronic Laboratory Notebooks like eLabFTW or SciNote can automatically ingest analysis results via REST APIs. Configure OpenMS to output results as mzTab files, then use a simple Python watcher script to upload completed analyses to your ELN:

```bash
#!/bin/bash
# Watch for completed MS analyses and upload to ELN
inotifywait -m /data/results/ -e create |
while read path action file; do
    if [[ "$file" == *.mzTab ]]; then
        curl -X POST https://eln.lab.local/api/experiments/           -H "Authorization: Bearer $ELN_TOKEN"           -F "file=@/data/results/$file"
    fi
done
```

**Metadata management**: MS experiments generate rich metadata — instrument settings, chromatography conditions, sample preparation protocols. Store this alongside your raw data using the ISA-Tab format or a custom SQLite database. MZmine 3 can export processing parameters as XML, which should be archived with each analysis run for full reproducibility.

**Long-term archival strategy**: Raw MS files should be archived in their native format for re-analysis with improved tools. Use the ProteoWizard `msconvert` to create compressed mzML copies for long-term storage (50-70% size reduction), and maintain a PostgreSQL database of experiment metadata for search and retrieval. Budget 2-5 TB per year of storage for an active proteomics lab running 2-3 instruments.

## FAQ

### Which tool should I start with for proteomics?

Start with ProteoWizard's msconvert to convert your vendor files to open mzML format, then use OpenMS for the actual analysis pipeline. This combination handles 95% of proteomics workflows and is the most documented pathway.

### Can I integrate these tools with Galaxy?

Yes — all three are available as Galaxy tools via the Galaxy Tool Shed. OpenMS has the most comprehensive Galaxy integration with 180+ tools. Our [bioinformatics workflow platforms guide](../2026-06-09-self-hosted-bioinformatics-workflow-platforms-galaxy-nfcore-cwl-guide/) covers Galaxy deployment in detail.

### How much storage do I need?

Budget 200-500 GB for active projects. Raw mass spectrometry files are large (1-10 GB each), and processing generates intermediate files 2-3x the raw size. Use tiered storage: NVMe for active processing, HDD array for completed projects.

### Do I need a Windows license for ProteoWizard?

ProteoWizard's msconvert runs natively on Linux via Wine, and Docker images include the necessary Wine configuration. For Thermo .raw files specifically, you'll need to either use the Docker image (which bundles vendor libraries) or convert on a Windows machine first.

### Can MZmine 3 process proteomics data?

MZmine 3 is optimized for small molecules (metabolomics/lipidomics), not peptides/proteins. For proteomics, use OpenMS or MaxQuant. For metabolomics, MZmine 3 and XCMS are the top open-source choices, with MZmine having the better GUI.

### How do I share results with collaborators?

Export to open formats: mzTab for identification results, mzML for processed spectra, and CSV for quantitative matrices. Upload to a self-hosted data portal or use iRODS for managed sharing. For interactive exploration, provide your collaborators access to the OpenMS TOPPView or a JupyterHub instance with pyOpenMS.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Mass Spectrometry and Proteomics Analysis: OpenMS vs ProteoWizard vs MZmine",
  "description": "In-depth comparison of OpenMS, ProteoWizard, and MZmine 3 for self-hosted mass spectrometry data analysis. Includes Docker Compose deployments, automated pipeline examples, and guidance for proteomics and metabolomics labs.",
  "datePublished": "2026-06-09",
  "dateModified": "2026-06-09",
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
