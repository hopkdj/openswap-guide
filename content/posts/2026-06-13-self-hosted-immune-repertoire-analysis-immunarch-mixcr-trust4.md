---
title: "Self-Hosted Immune Repertoire Analysis: immunarch vs MiXCR vs TRUST4"
date: "2026-06-13"
tags: ["immunoinformatics", "immune-repertoire", "bioinformatics", "tcr-analysis", "bcr-analysis", "adaptive-immunity"]
draft: false
---

## Introduction

The adaptive immune system maintains a vast library of T-cell receptors (TCRs) and B-cell receptors (BCRs) capable of recognizing virtually any pathogen. High-throughput sequencing now allows researchers to profile these immune repertoires at unprecedented depth — but analyzing the resulting data requires specialized computational tools that can handle the unique challenges of immune receptor sequences: extreme diversity, shared gene segments, and somatic hypermutation.

This guide compares three leading open-source tools for immune repertoire analysis: **immunarch**, **MiXCR**, and **TRUST4**. Each takes a different approach to the core tasks of repertoire analysis — from raw read assembly to clonotype identification and diversity quantification.

## Tool Overview

| Feature | immunarch | MiXCR | TRUST4 |
|---------|-----------|-------|--------|
| **Primary Function** | Exploratory analysis & visualization | End-to-end preprocessing & analysis | De novo TCR/BCR assembly |
| **Language** | R | Java | C++ |
| **GitHub Stars** | 338+ | 393+ | 354+ |
| **Input Format** | Clonotype tables (pre-processed) | Raw FASTQ files | RNA-seq FASTQ/BAM |
| **VDJ Assignment** | Not included (uses external) | Built-in (IMGT-aligned) | Built-in reference-based |
| **Diversity Metrics** | Comprehensive (20+ indices) | Basic (Shannon, clonality) | Limited |
| **License** | AGPL-3 | MIT | GPL-3 |
| **Container** | R Docker images | Docker + Conda | Docker available |

## Why Self-Host Immune Repertoire Analysis?

Immune repertoire data is among the most sensitive types of biomedical information. A person's TCR/BCR repertoire can reveal past infections, vaccination history, and even autoimmune disease status — making it effectively identifiable health data. Many institutional review boards require that immune repertoire sequencing data remain within institutional computing environments rather than being processed on third-party cloud platforms.

Self-hosting also addresses the scale challenge. A single 10x Genomics single-cell immune profiling experiment can generate 100+ GB of FASTQ data, and cohort studies multiply this by hundreds of samples. The network transfer time and cloud egress costs for uploading these datasets can exceed the actual compute costs. Colocating analysis infrastructure with sequencing instruments eliminates this bottleneck.

Finally, immune repertoire analysis is an iterative, exploratory process — researchers frequently re-run analyses with different parameters after visualizing initial results. The rapid feedback cycle of a local RStudio Server or JupyterHub deployment (versus cloud batch jobs with queuing delays) dramatically accelerates the research process. For complementary single-cell analysis infrastructure, see our [single-cell RNA-seq guide](../2026-06-10-self-hosted-single-cell-rna-seq-analysis-seurat-scanpy-monocle3/).

For foundational genomics processing, check our [genomic variant calling guide](../2026-06-10-self-hosted-genomic-variant-calling-gatk-freebayes-bcftools/).

## Installing immunarch with RStudio Server

immunarch is an R package designed for exploratory analysis of immune repertoire data, offering an extensive suite of visualization and diversity quantification tools:

```yaml
# docker-compose.yml for immunarch analysis environment
version: "3.8"
services:
  rstudio-immunarch:
    image: rocker/rstudio:4.4.0
    container_name: immunarch-env
    ports:
      - "8787:8787"
    environment:
      - PASSWORD=your_secure_password
      - ROOT=TRUE
    volumes:
      - ./data:/home/rstudio/data
      - ./output:/home/rstudio/output
    restart: unless-stopped
    mem_limit: 32g
```

Install immunarch within the R environment:

```r
# Install from CRAN
install.packages("immunarch")

# Load and explore
library(immunarch)

# Load example 10x Genomics data
data(immdata)
immdata$data  # list of samples

# Basic clonotype analysis
exp_vol <- repExplore(immdata$data, .method = "volume")
vis(exp_vol)

# Diversity estimation with multiple indices
div <- repDiversity(immdata$data, .method = "div")
vis(div)

# Gene usage analysis
gene_usage <- geneUsage(immdata$data, "hs.trbv")
vis(gene_usage)

# Clonotype tracking across time points
track <- trackClonotypes(immdata$data, 
    list(1, 5), .col = "aa")
vis(track)
```

## Installing MiXCR for Complete Pipeline Processing

MiXCR handles the full pipeline from raw sequencing reads to clonotype tables and downstream analysis:

```bash
# Download and install MiXCR
wget https://github.com/milaboratory/mixcr/releases/download/v4.7.0/mixcr-4.7.0.zip
unzip mixcr-4.7.0.zip
sudo mv mixcr /opt/mixcr
export PATH="/opt/mixcr:$PATH"

# Download reference V/D/J gene segments
mixcr download-human-reference

# Analyze paired-end TCR sequencing data
mixcr analyze generic-tcr-amplicon     --species hsa     --rna     --rigid-left-alignment-boundary     --floating-right-alignment-boundary C     sample_R1.fastq.gz     sample_R2.fastq.gz     sample_output

# Export clonotype table for immunarch
mixcr exportClones sample_output.clns sample_clones.txt

# Generate comprehensive QC report
mixcr exportQc align sample_output.vdjca sample_qc.pdf
```

For batch processing multiple samples:

```bash
# Create sample list
for sample in sample1 sample2 sample3; do
    mixcr analyze generic-tcr-amplicon         --species hsa --rna         ${sample}_R1.fastq.gz ${sample}_R2.fastq.gz         results/${sample} &
done
wait
```

## Installing TRUST4 for De Novo Assembly

TRUST4 assembles TCR/BCR sequences directly from bulk or single-cell RNA-seq data without requiring targeted immune sequencing:

```bash
# Clone and build TRUST4
git clone https://github.com/liulab-dfci/TRUST4.git
cd TRUST4
make -j 8

# Build reference index from IMGT database
perl build_barcoded_reference.pl     -f human_IMGT+C.fa     -o hg38_bcrtcr

# Run de novo assembly from RNA-seq BAM
./run-trust4     -f hg38_bcrtcr.fa     -1 sample_R1.fastq.gz     -2 sample_R2.fastq.gz     -t 8     -o sample_trust4     --barcode whitelist.txt

# Convert TRUST4 output to immunarch-compatible format
# TRUST4 outputs a *_report.tsv file with assembled CDR3 sequences
python3 convert_trust4_to_immunarch.py     --input sample_trust4_report.tsv     --output sample_immunarch.txt
```

## Analysis Workflow Comparison

A typical immune repertoire analysis workflow involves three stages: preprocessing, quantification, and interpretation. Here's how the tools complement each other:

**Stage 1 — Preprocessing**: MiXCR handles raw FASTQ to clonotype table conversion with the most mature error-correction pipeline. Its built-in PCR error correction and chimera filtering are essential for accurate clonotype calling. TRUST4 is preferred when working with bulk RNA-seq data (rather than targeted TCR-seq) since it can assemble immune receptors from transcriptomic reads.

**Stage 2 — Quantification**: immunarch provides the richest set of analysis methods — over 20 diversity indices, gene segment usage statistics, clonotype tracking, and repertoire overlap analysis. Its integration with the R ecosystem means you can seamlessly feed results into DESeq2 for differential abundance testing or ggplot2 for custom visualizations.

**Stage 3 — Interpretation**: For clinical applications like minimal residual disease (MRD) monitoring in leukemia, MiXCR's validated clonotype identification pipeline is the gold standard. For basic research on repertoire dynamics, the MiXCR → immunarch pipeline provides the most comprehensive analytical capability.

## Deployment Architecture for Immune Repertoire Pipelines

When deploying immune repertoire analysis at scale, consider a tiered architecture that separates concerns. Use MiXCR on a headless compute node (no GUI needed) for the computationally intensive preprocessing stage, processing raw FASTQ files into compact clonotype tables that are orders of magnitude smaller. These clonotype tables then feed into an RStudio Server instance running immunarch for interactive analysis, accessible via web browser on port 8787. This separation has practical benefits: the compute node can be a spot or preemptible instance with high CPU but no persistent storage, while the RStudio Server requires persistent storage for user workspaces but modest compute. For labs processing fifty or more samples weekly, this architecture reduces costs by allowing the expensive compute tier to scale down during idle periods while preserving the interactive analysis environment.

For integration with laboratory information management systems, both MiXCR and TRUST4 produce standardized output formats that can be parsed by automated quality control scripts. A simple Python watchdog service can monitor output directories for new clonotype files, run validation checks covering minimum read counts and clonotype diversity thresholds, and notify researchers via messaging platforms when analysis completes. This reduces the manual overhead of tracking dozens of parallel sequencing runs and ensures consistent quality standards across projects. For managing the bioinformatics infrastructure that supports these pipelines, refer to our guide on [bioinformatics workflow platforms](../2026-06-09-self-hosted-bioinformatics-workflow-platforms-galaxy-nfcore/).


## Frequently Asked Questions

### Can I use these tools for both T-cell and B-cell receptor analysis?

Yes, all three tools support both TCR and BCR analysis. MiXCR has dedicated analysis presets for TCR alpha/beta, TCR gamma/delta, BCR heavy chain, and BCR light chain (kappa/lambda) sequences. TRUST4 can assemble both TCR and BCR contigs from the same RNA-seq BAM file simultaneously. immunarch's data structures are agnostic to receptor type — the same analysis functions work for TCR and BCR data.

### How do I handle paired alpha-beta chain information?

This remains a challenge in bulk TCR sequencing. MiXCR can pair alpha-beta chains from single-cell data (10x Genomics VDJ assay) using cell barcodes. For bulk data, the chains are analyzed independently. immunarch provides functions for pairing analysis when cell barcode information is available. If you're specifically interested in paired-chain analysis, consider the scRepertoire or scirpy packages for single-cell immune profiling.

### What sequencing depth do I need for reliable immune repertoire analysis?

For targeted TCR-seq, 1-2 million reads per sample typically provides good coverage of the dominant clonotypes. For detecting rare clonotypes (frequency < 0.001%), 5-10 million reads are recommended. When using TRUST4 with bulk RNA-seq data, T-cell receptor reads typically comprise only 0.1-0.5 percent of total reads — for reliable detection, you need at least 50 million total RNA-seq reads per sample.

### How do I compare immune repertoires across different sequencing platforms?

MiXCR provides the most consistent cross-platform results because its alignment algorithm uses IMGT-defined gene segment boundaries rather than relying on platform-specific read characteristics. When comparing data from different platforms (e.g., Illumina vs MGI), always process all samples through the same MiXCR version with identical parameters. immunarch's normalization functions can then account for differences in sequencing depth.

### What are the privacy considerations for hosting immune repertoire data?

Immune repertoires are considered identifiable biomedical data in many jurisdictions. When self-hosting, ensure your analysis server uses full-disk encryption, access controls with multi-factor authentication, and comprehensive audit logging. For multi-institutional studies, consider deploying a federated analysis framework where analysis code moves to the data (rather than data moving to a central server) — both immunarch and MiXCR can operate within such frameworks.

### Can I integrate immune repertoire analysis with single-cell gene expression data?

Yes, this is one of the most powerful applications. After processing the VDJ data with MiXCR (for the immune receptor sequences) and the gene expression data with Cell Ranger or STARsolo, you can link clonotype information to transcriptomic cell states. The immunarch package can import both the clonotype table and the Seurat/SingleCellExperiment object, then overlay clonotype expansion status onto UMAP visualizations using its built-in integration functions.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Immune Repertoire Analysis: immunarch vs MiXCR vs TRUST4",
  "description": "Comprehensive comparison of immunarch, MiXCR, and TRUST4 for self-hosted immune repertoire analysis. Includes Docker Compose configurations, installation guides, diversity analysis workflows, and TCR/BCR pipeline integration.",
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
