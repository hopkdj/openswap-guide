---
title: "Self-Hosted Comparative Genomics Pipelines: Cactus vs MUMmer vs LASTZ vs SibeliaZ"
date: "2026-06-13"
tags: ["bioinformatics", "comparative-genomics", "genome-alignment", "genomics", "scientific-computing", "whole-genome"]
draft: false
---

## Introduction

Comparative genomics — the systematic comparison of whole genomes across species — reveals evolutionary relationships, identifies conserved functional elements, and tracks genomic rearrangements. With sequencing costs continuing to drop and thousands of new genomes published annually, the computational tools for aligning and comparing entire genomes have become essential infrastructure for modern biology.

This guide compares four leading open-source whole-genome alignment and comparison tools: **Cactus** (progressive genome aligner), **MUMmer** (suffix-tree based aligner), **LASTZ** (pairwise aligner), and **SibeliaZ** (de Bruijn graph-based aligner). Each tool approaches the challenge of genome comparison from a different algorithmic angle, making them suited to different scales and types of analysis.

## Comparison Overview

| Feature | Cactus | MUMmer4 | LASTZ | SibeliaZ |
|---------|--------|---------|-------|----------|
| **Alignment Type** | Progressive multiple | Pairwise | Pairwise | Multiple whole-genome |
| **Algorithm** | Cactus graph | Suffix tree | Seed-and-extend | de Bruijn graph |
| **Input Scale** | Hundreds of genomes | Two genomes | Two genomes | Dozens of genomes |
| **Output** | HAL alignment + VCF | SNPs, structural variants | MAF/Lav alignment | Synteny blocks |
| **Language** | Python/C | C++ | C | C++ |
| **GitHub Stars** | 686+ | 561+ | 250+ | 160+ |
| **Docker** | Yes | Bioconda | Bioconda | Bioconda |
| **Memory Usage** | High (50+ GB) | Moderate (8-32 GB) | High (16-64 GB) | Very High (64+ GB) |
| **Best For** | Multi-species alignments | Bacterial genomes | Pairwise with rearrangements | Synteny discovery |

## Why Self-Host Comparative Genomics?

Whole-genome alignment is computationally intensive and often involves proprietary or pre-publication genome sequences that cannot be uploaded to public web services. Self-hosting comparative genomics pipelines ensures data confidentiality while providing the computational resources needed for large-scale analyses. For agricultural biotech companies comparing crop varieties, pharmaceutical researchers tracking pathogen evolution, or evolutionary biologists studying speciation, local infrastructure is non-negotiable.

The computational demands of these tools also make cloud-based pay-per-use models expensive for routine use. A single Cactus run aligning 50 mammalian genomes can consume 500+ CPU-hours; on AWS, that translates to hundreds of dollars per analysis. A dedicated on-premises server pays for itself within months for labs running weekly comparative analyses. After alignment, downstream analysis often involves [genomic variant calling](../2026-06-10-self-hosted-genomic-variant-calling-gatk-freebayes-bcftools/) to identify SNPs, indels, and structural variants between the aligned genomes.

Comparative genomics also builds on foundational sequence analysis steps. Before aligning genomes, you typically need [high-quality genome assemblies](../2026-06-09-self-hosted-genome-assembly-spades-canu-flye-hifiasm-guide/) and possibly [multiple sequence alignments of gene families](../2026-06-13-self-hosted-multiple-sequence-alignment-mafft-muscle-clustalo-tcoffee-kalign/). The aligned genomes then feed into [phylogenetic tree inference](../2026-06-10-self-hosted-phylogenetic-tree-inference-iqtree-raxml-beast-mrbayes/) for evolutionary analysis.

## Running Cactus for Progressive Multiple Genome Alignment

Cactus uses a novel graph-based approach to progressively align hundreds of genomes, handling complex rearrangements automatically. It is the tool of choice for large-scale multi-species alignment projects like the Zoonomia Project and Vertebrate Genomes Project.

```bash
# Install via Conda
conda create -n cactus -c bioconda cactus
conda activate cactus

# Create a seqFile listing genomes
cat > seqfile.txt << 'EOF'
human /data/genomes/human.fa
chimp /data/genomes/chimp.fa
mouse /data/genomes/mouse.fa
rat /data/genomes/rat.fa
dog /data/genomes/dog.fa
EOF

# Run progressive alignment with phylogenetic guide tree
cactus jobStore ./cactus-seqfile.txt output.hal \
  --root human --defaultDisk 50G --maxCores 32

# Export alignment in MAF format
hal2maf output.hal alignment.maf --refGenome human

# Call variants from the alignment
hal2vcf output.hal human --hdf5InMemory > variants.vcf
```

The HAL (Hierarchical Alignment Format) output preserves the full multi-genome alignment structure, enabling efficient random access to any region across all aligned species. Cactus also produces VCF files for any reference genome, making it straightforward to integrate with variant analysis pipelines.

For large-scale projects, Cactus supports distributed execution on clusters:

```bash
# Run on Slurm/Torque cluster
cactus --batchSystem slurm --maxCores 128 \
  --defaultMemory 64G ./cactus-seqfile.txt output.hal
```

## Using MUMmer4 for High-Sensitivity Pairwise Comparison

MUMmer4 is the gold standard for pairwise genome alignment, particularly for bacterial genomes and closely related eukaryotic genomes. Its suffix-tree algorithm finds all maximal unique matches (MUMs) efficiently, providing comprehensive variant detection.

```bash
# Install via Conda
conda install -c bioconda mummer4

# Align two genomes
nucmer --maxmatch --threads 32 \
  reference.fa query.fa --prefix comparison

# Find SNPs
show-snps -Clr comparison.delta > snps.txt

# Detect structural rearrangements
mummerplot --png --layout --large comparison.delta \
  -p comparison_plot

# One-to-one alignment (for complete genomes)
delta-filter -1 comparison.delta > filtered.delta
show-coords -rcl filtered.delta > alignment_coords.txt
```

MUMmer4 excels at detecting structural variants, inversions, and translocations between genomes. For prokaryotic genomes, it can align complete chromosomes in seconds, making it ideal for outbreak investigations and strain comparison workflows. The mummerplot visualization generates dot plots that reveal large-scale rearrangements at a glance.

For assembly validation, MUMmer can compare your assembly against a reference to identify misassemblies:

```bash
# Assembly-to-reference comparison
dnadiff -d comparison.delta -p assembly_qc
# Produces: assembly_qc.report (summary statistics)
```

## Performing Pairwise Alignment with LASTZ

LASTZ is a descendant of the BLASTZ program, optimized for aligning diverged sequences from different species. It is the engine behind the UCSC Genome Browser's multi-species alignments and remains the tool of choice for cross-species pairwise comparisons involving extensive rearrangements.

```bash
# Install via Conda
conda install -c bioconda lastz

# Basic pairwise alignment
lastz reference.fa[multiple] query.fa[multiple] \
  --format=maf --strand=both \
  --hspthresh=3000 --inner=2000 \
  --output=alignment.maf

# Chained/net alignment (for whole-genome scale)
lastz reference.fa query.fa > raw.maf
maf-chain raw.maf > chained.chain
chain-net chained.chain > netted.net

# Convert to PSL for UCSC Genome Browser
maf-convert psl alignment.maf > alignment.psl
```

LASTZ uses a seed-and-extend strategy with configurable scoring parameters that can be tuned for different evolutionary distances. The `--hspthresh` (high-scoring pair threshold) and `--inner` (gap extension penalty) parameters are critical for controlling sensitivity: lower thresholds detect more distant homologies but increase runtime. LASTZ is particularly effective at detecting conserved non-coding elements across species.

For mammalian genome comparisons, the recommended parameter set balances sensitivity and specificity:

```bash
# Tuned for human-mouse comparison (~90 Mya divergence)
lastz reference.fa query.fa \
  K=2400 L=3000 H=2000 Y=3400 \
  --format=axt --output=alignment.axt
```

## Discovering Synteny with SibeliaZ

SibeliaZ uses de Bruijn graphs to rapidly compare dozens of bacterial genomes for synteny block discovery. It is uniquely suited for pan-genome analysis, identifying conserved genomic neighborhoods and tracking gene order evolution across strain collections.

```bash
# Install via Conda
conda install -c bioconda sibeliaz

# Compare multiple bacterial genomes
sibeliaz -k 25 -t 32 \
  genome1.fna genome2.fna genome3.fna genome4.fna \
  -o synteny_output

# Output: synteny blocks in MAF-like format
# blocks_coords.txt - coordinates of synteny blocks
# blocks.txt - sequence of synteny blocks
```

SibeliaZ is orders of magnitude faster than progressive alignment approaches for bacterial-scale genomes (typically 3-6 Mbp each). It can compare 50+ E. coli strains on a single server, detecting shared synteny blocks, horizontally transferred regions, and genomic islands. For researchers studying bacterial evolution, antimicrobial resistance spread, or industrial strain optimization, SibeliaZ provides a rapid survey of genome-scale structural variation.

## Performance and Resource Requirements

Comparative genomics tools vary dramatically in their computational requirements, and choosing the right tool for your hardware is essential for practical deployment.

| Scenario | Tool | Genomes | CPU Hours | Peak RAM | Output Size |
|----------|------|---------|-----------|----------|-------------|
| 5 vertebrates (3 Gbp each) | Cactus | 5 | 48-96 | 64 GB | ~50 GB HAL |
| 2 bacterial genomes (5 Mbp) | MUMmer4 | 2 | 0.01 | 2 GB | ~5 MB |
| Human vs mouse (3 Gbp) | LASTZ | 2 | 24-48 | 32 GB | ~20 GB MAF |
| 30 bacterial strains (5 Mbp) | SibeliaZ | 30 | 2-4 | 128 GB | ~500 MB |

For bacterial genome comparisons, MUMmer4 is the clear winner in speed and efficiency. For multi-species vertebrate alignments, Cactus is the only tool capable of progressive alignment at that scale, though it requires significant computational investment. LASTZ fills the niche of deeply diverged pairwise comparison where neither MUMmer (too diverged) nor Cactus (overkill for 2 genomes) is ideal.

## Choosing the Right Comparative Genomics Tool

**Choose Cactus** for large-scale multi-species alignment projects involving 5+ eukaryotic genomes. If you're participating in a genome consortium, building a reference alignment for a taxonomic clade, or need the HAL format for random-access queries, Cactus is the standard. It handles complex rearrangement histories automatically through the Cactus graph structure.

**Choose MUMmer4** for routine pairwise comparisons, especially of bacterial genomes or assembly validation. Its speed, low memory footprint, and comprehensive output (SNPs, indels, structural variants, dot plots) make it the daily driver for most comparative genomics tasks. It is also the best choice for outbreak analysis and strain tracking.

**Choose LASTZ** when you need sensitive pairwise alignment between highly diverged species (e.g., human vs chicken, or plant genomes with extensive rearrangements). LASTZ's tunable parameters make it adaptable to a wide range of evolutionary distances, and its output integrates directly with the UCSC Genome Browser and downstream chain/net tools.

**Choose SibeliaZ** for rapid synteny analysis across dozens of bacterial genomes or for pan-genome surveys. If you need to identify conserved gene order, horizontally transferred regions, or genomic islands across a strain collection, SibeliaZ provides results in minutes that would take hours with progressive aligners.

## FAQ

### Which tool should I use for bacterial genome comparison?

MUMmer4 is the preferred choice for bacterial genomes. It can align two 5 Mbp genomes in under a second, produces comprehensive variant calls (SNPs, indels, structural variants), and generates publication-quality dot plots. For comparing dozens of bacterial strains to discover conserved synteny blocks, SibeliaZ scales much better than pairwise approaches. For 3-10 bacterial genomes where you want a full multiple alignment, consider progressiveMauve or Cactus with appropriate parameters.

### How much RAM do I need for mammalian genome alignments?

LASTZ requires 16-32 GB for human-mouse scale comparisons. Cactus needs 64-128 GB for 5-way mammalian alignments and can require 256+ GB for 20+ species. MUMmer4 is the most memory-efficient, handling human-scale genomes in 8-32 GB. If your server has limited RAM, use MUMmer4 for pairwise and consider cloud bursting for multi-species Cactus runs. The memory bottleneck is typically during the database construction phase, not the alignment itself.

### Can I use these tools for plant genomes?

Yes, but with caveats. Plant genomes are often larger and more repetitive than animal genomes, which increases runtime for all tools. Polyploidy (multiple genome copies) further complicates alignment. Cactus handles polyploid genomes natively. For LASTZ, use more stringent masking of repetitive elements and consider the `--notransition` flag to improve performance. MUMmer4 works for moderate-sized plant genomes (up to ~1 Gbp) but may struggle with very large genomes like wheat (17 Gbp). For complex plant genomes, consider splitting alignments by chromosome or linkage group.

### What output formats should I expect?

Each tool has its native format: Cactus uses HAL (Hierarchical Alignment Format), MUMmer uses delta files (binary alignment format), LASTZ defaults to MAF (Multiple Alignment Format), and SibeliaZ outputs custom synteny block coordinates. All can be converted to MAF for interoperability, and most provide VCF output for variant calling. For visualization, MUMmer produces dot plots, Cactus alignments can be viewed in the UCSC Browser via HAL tools, and LASTZ MAF files work with most genome browsers. Consider storing HAL files for archival purposes since they preserve the complete alignment graph for future queries.

### How do these tools fit into a pipeline with genome annotation and phylogenetic analysis?

A typical comparative genomics pipeline follows this progression: (1) Assemble genomes with [SPAdes, Canu, or hifiasm](../2026-06-09-self-hosted-genome-assembly-spades-canu-flye-hifiasm-guide/), (2) Align genomes using Cactus or MUMmer, (3) Call variants from the alignment, (4) Extract conserved regions for [phylogenetic tree inference](../2026-06-10-self-hosted-phylogenetic-tree-inference-iqtree-raxml-beast-mrbayes/), and (5) Annotate genes with BRAKER or funannotate on each genome. Tools like TOGA (Tool to infer Orthologs from Genome Alignments) can project annotations between species using Cactus alignments. For gene-family-level analysis, use the aligned genomes to extract orthologous groups and build gene trees.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Comparative Genomics Pipelines: Cactus vs MUMmer vs LASTZ vs SibeliaZ",
  "description": "Compare four open-source whole-genome alignment tools for self-hosted comparative genomics: Cactus (progressive multiple alignment), MUMmer4 (suffix-tree pairwise alignment), LASTZ (seed-and-extend pairwise), and SibeliaZ (de Bruijn graph synteny). Includes installation, performance benchmarks, and integration with phylogenetic analysis.",
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
