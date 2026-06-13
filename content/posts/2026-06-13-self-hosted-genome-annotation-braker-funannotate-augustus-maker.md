---
title: "Self-Hosted Genome Annotation Pipelines: BRAKER vs funannotate vs AUGUSTUS vs MAKER"
date: "2026-06-13"
tags: ["bioinformatics", "genome-annotation", "gene-prediction", "genomics", "scientific-computing", "transcriptomics"]
draft: false
---

## Introduction

Genome annotation — the process of identifying genes, regulatory elements, and functional features within a sequenced genome — transforms raw DNA sequences into biologically meaningful information. Whether you are working with a newly sequenced eukaryotic genome, updating annotations for a model organism, or annotating metagenomic contigs, choosing the right annotation pipeline significantly impacts the quality and usability of your results.

This guide compares four leading open-source genome annotation tools: **BRAKER** (automated gene prediction with RNA-seq evidence), **funannotate** (comprehensive eukaryotic annotation pipeline), **AUGUSTUS** (ab initio gene prediction engine), and **MAKER** (evidence-based genome annotation pipeline). Each occupies a different niche in the annotation ecosystem, from fully automated workflows to manually curated, evidence-driven pipelines.

## Comparison Overview

| Feature | BRAKER | funannotate | AUGUSTUS | MAKER |
|---------|--------|-------------|----------|-------|
| **Approach** | Automated (RNA-seq + protein) | Full pipeline | Ab initio prediction | Evidence-driven |
| **Input Required** | Genome + RNA-seq/proteins | Genome + RNA-seq + proteins | Genome + HMM parameters | Genome + multiple evidence |
| **Web Interface** | No (CLI) | No (CLI) | Web server available | No (CLI) |
| **Output** | GFF3 gene predictions | GFF3 + functional annotation | GFF3 gene models | GFF3 + evidence tracks |
| **Language** | Perl/Python | Python | C++ | Perl |
| **GitHub Stars** | 463+ | 388+ | 335+ | 44+ |
| **Docker Support** | Singularity/Docker | Conda/Bioconda | Docker (community) | Conda |
| **Speed (eukaryotic)** | 2-4 hours | 4-8 hours | 1-2 hours | 12-48 hours |
| **Functional Annotation** | No (structural only) | Yes (InterPro, GO, KEGG) | No | Via InterProScan |
| **Best For** | Rapid first-pass annotation | Comprehensive functional annotation | High-quality ab initio models | Manual curation projects |

## Why Self-Host Genome Annotation?

Public genome annotation services like NCBI's Eukaryotic Genome Annotation Pipeline or Ensembl's annotation system work well for model organisms and frequently studied species, but they impose significant limitations. Your genome may sit in a queue for months before annotation begins, you have limited control over the evidence used, and the pipeline parameters are fixed. For non-model organisms, niche species, or proprietary genomes, self-hosting annotation pipelines is the only practical path to publication-ready gene models.

The quality gap between automated public services and self-hosted annotation with organism-specific evidence is substantial. Incorporating your own RNA-seq data, protein homology evidence from closely related species, and repeat libraries tuned to your genome's repeat content can increase gene prediction accuracy by 15-30% compared to generic annotation. For agricultural genomics, where accurate gene models directly impact breeding decisions, or for pharmaceutical target discovery, where missing a single gene could mean missing a drug target, this accuracy difference matters.

Self-hosting also enables iterative annotation improvement. As new RNA-seq data, Iso-Seq long reads, or proteomics evidence becomes available, you can re-run the pipeline with expanded evidence — something not possible with one-shot public services. Once annotated, you can explore your gene models visually with a [self-hosted genome browser](../2026-06-09-self-hosted-genomics-browsers-jbrowse2-igv-web-ucsc/) or feed the protein sequences into [sequence search pipelines](../2026-06-09-self-hosted-genome-assembly-spades-canu-flye-hifiasm-guide/) for functional characterization.

## Running BRAKER for Automated Gene Prediction

BRAKER combines evidence from RNA-seq alignments and protein homology into a fully automated gene prediction pipeline. It trains AUGUSTUS and GeneMark-EP+ on your specific genome, eliminating the need for manual parameter tuning — a major advantage for non-model organisms.

```bash
# Install BRAKER via Conda
conda create -n braker -c bioconda braker3
conda activate braker

# Align RNA-seq reads to genome
hisat2-build genome.fa genome_index
hisat2 -x genome_index -1 rna_r1.fq -2 rna_r2.fq \
  | samtools sort -o rna.bam -
samtools index rna.bam

# Run BRAKER with RNA-seq and protein evidence
braker.pl --genome=genome.fa \
  --bam=rna.bam \
  --prot_seq=orthodb_proteins.fa \
  --threads 32 \
  --workingdir=braker_output

# Output: braker_output/braker.gff3 (gene predictions)
#         braker_output/augustus.hints.gff (training hints)
```

BRAKER3, the latest version, integrates GeneMark-EP+ and AUGUSTUS with automatic training on both RNA-seq and protein evidence. It produces GFF3 annotation files that are compatible with downstream tools like BUSCO for quality assessment and JBrowse for visualization.

```bash
# Assess annotation completeness with BUSCO
busco -i braker_output/braker.aa -l eukaryota_odb10 \
  -o busco_results -m proteins --cpu 32
```

## Annotating Eukaryotic Genomes with funannotate

funannotate provides a comprehensive, opinionated annotation pipeline that takes raw genome assembly and RNA-seq data through to functionally annotated, publication-ready gene models. Unlike BRAKER, which produces only structural gene models, funannotate annotates each predicted gene with functional information from InterProScan, Pfam, GO terms, and KEGG pathways.

```bash
# Install funannotate
conda create -n funannotate -c bioconda funannotate
conda activate funannotate

# Set up the annotation database
funannotate setup -i all -d /data/funannotate_db

# Clean and soft-mask the genome
funannotate clean -i genome.fa -o genome_cleaned.fa
funannotate mask -i genome_cleaned.fa -o genome_masked.fa \
  --cpus 32

# Train ab initio gene predictors
funannotate train -i genome_masked.fa \
  -o training_output \
  --left rna_r1.fq --right rna_r2.fq \
  --species "My Organism" --cpus 32

# Predict and functionally annotate genes
funannotate predict -i genome_masked.fa \
  -o predict_output \
  -s "My Organism" \
  --rna_bam rna.bam \
  --protein_evidence uniprot_sprot.fa \
  --cpus 32

# Functional annotation against multiple databases
funannotate annotate -i predict_output \
  -o final_annotation \
  --cpus 32 \
  --iprscan /data/interproscan
```

funannotate's output includes multiple file formats ready for NCBI submission: GFF3, GenBank, and EMBL formats, plus functional annotation tables and summary statistics. It also generates publication-quality figures summarizing gene structure statistics, functional category distributions, and BUSCO completeness scores.

## Using AUGUSTUS for Ab Initio Gene Prediction

AUGUSTUS is the most accurate ab initio gene prediction tool available, using a generalized hidden Markov model (GHMM) trained on species-specific parameters. While BRAKER and funannotate wrap AUGUSTUS internally, running AUGUSTUS directly gives fine-grained control over prediction parameters and is useful for iterative model improvement.

```bash
# Install AUGUSTUS via Conda
conda create -n augustus -c bioconda augustus
conda activate augustus

# List available pre-trained species parameters
augustus --species=help

# Run gene prediction with pre-trained parameters
augustus --species=human \
  --strand=both \
  --genemodel=complete \
  --gff3=on \
  genome.fa > predictions.gff3

# Train custom species parameters (requires BRAKER or manual training)
# Using evidence hints from RNA-seq alignments:
augustus --species=my_species \
  --hintsfile=rna_hints.gff \
  --extrinsicCfgFile=extrinsic.cfg \
  genome.fa > predictions_with_hints.gff3

# Run the AUGUSTUS web server locally for interactive use
# (available through the AUGUSTUS Docker image)
```

AUGUSTUS is particularly powerful when combined with evidence-based hints from RNA-seq, protein alignments, and repeat masking. The extrinsic configuration file (`extrinsic.cfg`) controls how different evidence types are weighted, allowing biologists to fine-tune predictions for specific genomic features:

```bash
# Example extrinsic.cfg for high-confidence RNA-seq evidence
cat > extrinsic.cfg << 'EOF'
[SOURCES]
M RM

[GENERAL]
start 1 1 0.9
stop  1 1 0.9

[M]
B 0.8 1 0.5
E 0.8 1 0.5

[RM]
repeats 0 1 0.7
EOF
```

## Running MAKER for Evidence-Driven Annotation

MAKER is the veteran annotation pipeline, designed for projects where manual curation and evidence integration are priorities. It iteratively runs ab initio predictors (SNAP, AUGUSTUS, GeneMark), aligns EST and protein evidence, and produces GFF3 output with detailed evidence tracks.

```bash
# Install MAKER via Conda
conda create -n maker -c bioconda maker
conda activate maker

# Create MAKER control files
maker -CTL
# Generates: maker_opts.ctl, maker_bopts.ctl, maker_exe.ctl

# Edit maker_opts.ctl with genome and evidence paths
# genome=genome.fa
# est=transcriptome.fa
# protein=uniprot_sprot.fa
# augustus_species=your_species

# Run MAKER
maker -base annotation_run \
  maker_opts.ctl maker_bopts.ctl maker_exe.ctl \
  -cpus 32

# Merge GFF3 output files
gff3_merge -d annotation_run.maker.output/annotation_run_master_datastore_index.log

# Generate quality statistics
maker_map_ids --prefix MyOrg_ --justify 6 annotation_run.all.gff > genome.all.gff
```

MAKER's strength lies in its iterative refinement process. After the initial run, you can train SNAP and AUGUSTUS on the high-confidence gene models from the first pass, then re-run MAKER with the improved ab initio parameter files for higher accuracy. MAKER also preserves all evidence alignments in the output GFF3, enabling detailed inspection of which evidence supports each gene model — essential for manual curation.

## Performance Benchmarks and Scaling

Annotation pipeline performance varies dramatically based on genome size, evidence volume, and computational resources:

| Pipeline | Genome (100 Mbp) | Genome (1 Gbp) | RAM Required | Storage Output |
|----------|-----------------|----------------|--------------|----------------|
| BRAKER3 | 1-2 hours | 4-8 hours | 16-32 GB | ~50 MB |
| funannotate | 2-4 hours | 8-16 hours | 32-64 GB | ~200 MB |
| AUGUSTUS (alone) | 15-30 min | 1-3 hours | 4-8 GB | ~30 MB |
| MAKER | 4-8 hours | 24-48 hours | 16-32 GB | ~500 MB |

BRAKER provides the best balance of speed and accuracy for rapid annotation of newly assembled genomes. funannotate is worth the additional runtime when functional annotation (GO terms, InterPro domains, KEGG pathways) is required. AUGUSTUS alone is fast but requires pre-trained parameters — making BRAKER's automated training essential for non-model organisms. MAKER's longer runtime reflects its evidence-driven, iterative approach that produces the most thoroughly supported gene models.

## Choosing the Right Annotation Pipeline

**Choose BRAKER** when you have a newly assembled eukaryotic genome and need rapid, automated structural annotation. It is ideal for genome project first passes, comparative genomics studies requiring consistent gene calls across multiple species, and situations where you lack species-specific training parameters. BRAKER3's integration of both RNA-seq and protein evidence produces high-quality models with minimal manual intervention.

**Choose funannotate** when you need a complete, submission-ready annotation including functional information. It is the best choice for projects destined for NCBI submission, publications requiring GO/KEGG enrichment analysis, or any scenario where functional annotation matters as much as gene structure. funannotate's opinionated workflow reduces the degrees of freedom that can lead to inconsistent annotations between projects.

**Choose AUGUSTUS directly** when you have pre-trained species parameters and want fine-grained control over the prediction process, or when you're iteratively improving an existing annotation. Its web server mode enables interactive exploration of gene predictions, and its hint system allows integration of diverse evidence types with configurable weighting schemes.

**Choose MAKER** when evidence integration and manual curation are priorities. It excels in projects where annotation quality must be documented with evidence tracks, such as reference genome projects, model organism databases, and regulatory submissions. MAKER's iterative training cycle (predict → train → re-predict) produces progressively improving annotations over multiple rounds.

## FAQ

### Do I need RNA-seq data for genome annotation?

For eukaryotic genomes, RNA-seq data dramatically improves annotation accuracy — typically increasing gene prediction sensitivity by 10-25% compared to ab initio-only approaches. BRAKER can work with protein evidence alone (from OrthoDB or UniProt), but combined RNA-seq + protein evidence yields the best results. For prokaryotic genomes, ab initio tools like Prokka or Bakta often suffice without transcriptomic data. If RNA-seq data isn't available for your species, phylogenetically close species' protein sets can serve as partial substitutes, though gene models for rapidly evolving genes may be missed.

### How do I assess the quality of my genome annotation?

BUSCO (Benchmarking Universal Single-Copy Orthologs) is the standard metric for annotation completeness. Run BUSCO on your predicted protein sequences against the appropriate lineage dataset (e.g., eukaryota_odb10, fungi_odb10, insecta_odb10). A score of >90% complete BUSCOs indicates high-quality annotation. Additionally, compare your gene count and length distributions to closely related species with published annotations — large deviations may indicate annotation errors. For functional annotation quality, check the percentage of genes with InterPro domain assignments (typically 60-85% for well-annotated eukaryotic genomes).

### Can these pipelines annotate non-model organisms with no close relatives?

Yes, but with reduced accuracy. AUGUSTUS and GeneMark-EP+ (used internally by BRAKER) perform best when trained on species-specific parameters. For truly novel lineages, use BRAKER's self-training mode, which iteratively refines gene models without external training data. funannotate uses a more conservative approach that may miss rapidly evolving genes but produces fewer false positives. Expect BUSCO completeness scores 5-15% lower for isolated taxa compared to model organisms. Consider supplementing with Iso-Seq long-read data, which captures full-length transcripts and is particularly valuable for organisms with no close reference species.

### What compute resources do I need for a large plant genome?

Plant genomes are challenging due to their size (often 500 Mbp - 17 Gbp) and repeat content. For a 1 Gbp plant genome: BRAKER needs 32-64 GB RAM and 4-8 hours with 32 cores. funannotate requires 64-128 GB RAM and 8-24 hours. MAKER demands 64+ GB RAM and may take 48+ hours. Repeat masking is critical for plants — use RepeatModeler to build a de novo repeat library before annotation. Consider splitting the genome by chromosome for parallel processing, then merging the GFF3 outputs. For very large genomes like wheat (17 Gbp), consider annotating only gene space by masking repeats first and using a targeted approach with extensive RNA-seq evidence.

### How do I integrate annotation results with genome browsers and downstream analysis?

All pipelines produce GFF3 output, which is the standard format for genome browsers. After annotation, load your genome and GFF3 into [JBrowse 2 or IGV-Web](../2026-06-09-self-hosted-genomics-browsers-jbrowse2-igv-web-ucsc/) for interactive exploration. For functional analysis, extract protein sequences from the GFF3 and run them through [InterProScan or EggNOG-mapper](../2026-06-13-self-hosted-structural-bioinformatics-biopython-prody-pdb-tools/) for domain and pathway annotation. The annotated proteins can then be compared across species using alignment tools. For publication-ready figures, funannotate generates summary plots automatically, while custom visualization can be built with the GFF3 toolkit (gffread, AGAT) and plotting libraries.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Genome Annotation Pipelines: BRAKER vs funannotate vs AUGUSTUS vs MAKER",
  "description": "Compare four open-source genome annotation pipelines for self-hosted deployment: BRAKER (automated gene prediction), funannotate (comprehensive annotation), AUGUSTUS (ab initio prediction engine), and MAKER (evidence-driven annotation). Includes installation, performance benchmarks, and quality assessment with BUSCO.",
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
