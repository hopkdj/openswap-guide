---
title: "Self-Hosted Neural Spike Sorting Tools: SpikeInterface vs Kilosort vs Phy"
date: "2026-06-10"
tags: ["electrophysiology", "neuroscience", "spike-sorting", "neural-data", "scientific-computing", "python", "brain-research", "self-hosted"]
draft: false
---

## Introduction

Understanding how the brain processes information requires recording the activity of individual neurons. Modern high-density neural probes like Neuropixels can simultaneously record from hundreds to thousands of neurons, producing terabytes of raw electrophysiology data per experiment. The computational challenge lies in **spike sorting** — the process of separating the combined electrical signals into spike trains belonging to individual neurons.

Three open-source tools have become essential infrastructure in systems neuroscience: **SpikeInterface** provides a unified Python framework for the entire spike sorting pipeline; **Kilosort** is the dominant spike sorting algorithm optimized for high-density probes; and **Phy** is the gold-standard manual curation GUI. Together, they form a complete self-hosted pipeline for neural data analysis.

| Feature | SpikeInterface | Kilosort | Phy |
|---------|---------------|----------|-----|
| Primary Role | Unified framework/pipeline | Automated spike sorting | Manual curation GUI |
| License | MIT | BSD-3-Clause | MIT |
| GitHub Stars | 799+ | 615+ | 418+ |
| Input Formats | 30+ (OpenEphys, SpikeGLX, Neuralynx, etc.) | Binary, Neuropixels | Kwik, SpikeGLX |
| Algorithms Supported | 12+ sorters (Kilosort, SpykingCircus, HDSort, etc.) | Template matching (Kilosort 1-4) | Visualization only |
| GPU Acceleration | Via sorters | ✅ CUDA required (Kilosort 2.5+) | N/A |
| Preprocessing | ✅ Filtering, CAR, whitening | ✅ Built-in drift correction | N/A |
| Post-processing | ✅ Quality metrics, curation, export | ⚠️ Basic metrics | ✅ Manual merge/split/label |
| Python API | Native | MATLAB/Python wrapper | Python backend |
| Docker Support | ✅ pip/conda | ⚠️ MATLAB Runtime required | ✅ pip install |

## Installation and Setup

Setting up a complete spike sorting pipeline requires coordinating several components.

### SpikeInterface Installation

```bash
# Create a dedicated conda environment
conda create -n spikeinterface python=3.10
conda activate spikeinterface

# Install SpikeInterface and all sorters
pip install spikeinterface[full]

# Install specific sorters
pip install kilosort
pip install spykingcircus
pip install mountainsort5

# Verify
python -c "import spikeinterface; print(spikeinterface.__version__)"
```

### Kilosort Setup

```bash
# Kilosort requires MATLAB Runtime or Python wrapper
# Option A: Python wrapper (recommended for self-hosted setups)
git clone https://github.com/MouseLand/Kilosort.git
cd Kilosort
# Install the pykilosort wrapper
pip install pykilosort

# Option B: Docker with MATLAB Runtime
docker pull kilosort/kilosort4:latest

# Run sorting on a binary file
docker run --gpus all -v $(pwd)/data:/data \
  kilosort/kilosort4:latest /data/recording.bin /data/output
```

### Phy Curation Environment

```bash
# Phy is pure Python — simple installation
pip install phy phycontrib

# Launch the GUI for manual curation
phy template-gui params.py

# For headless server with web-based GUI
pip install phy-web
phy-web launch params.py --port 8888
```

## The Spike Sorting Pipeline: A Complete Workflow

A typical analysis proceeds through four stages. Here is how the tools work together:

```python
import spikeinterface as si
import spikeinterface.preprocessing as spre
import spikeinterface.sorters as ss
import spikeinterface.postprocessing as spost
import spikeinterface.qualitymetrics as sqm
import spikeinterface.exporters as sexp

# 1. LOAD: Read raw data in any format
recording = si.read_spikeglx('/data/neuropixels_recording')
# Also supports: si.read_openephys(), si.read_neuralynx(), si.read_intan()

# 2. PREPROCESS: Filter and clean
recording_f = spre.bandpass_filter(recording, freq_min=300, freq_max=6000)
recording_cmr = spre.common_reference(recording_f, reference='global')
recording_clean = spre.whiten(recording_cmr)

# 3. SORT: Run automated spike sorting
sorting = ss.run_sorter(
    'kilosort4',
    recording_clean,
    output_folder='/data/ks4_output',
    docker_image=True,
    verbose=True
)

# 4. POSTPROCESS: Extract waveforms, compute quality metrics
we = spost.extract_waveforms(
    recording_clean, sorting, '/data/waveforms',
    ms_before=1.0, ms_after=2.0, max_spikes_per_unit=500
)

# Compute quality metrics for each unit
metrics = sqm.compute_quality_metrics(we, metric_names=[
    'snr', 'isi_violation', 'amplitude_cutoff', 'presence_ratio'
])

# Filter good units
good_units = metrics.query('snr > 3.0 and isi_violation < 0.5').index
print(f"Found {len(good_units)} good units out of {len(metrics)} total")

# 5. EXPORT: Save clean data for Phy curation
sexp.export_to_phy(recording_clean, sorting, '/data/phy_export',
                    copy_binary=True, remove_if_exists=True)
```

### Manual Curation with Phy

After automated sorting, Phy provides interactive visualization for quality control:

```bash
# Launch Phy on the exported dataset
cd /data/phy_export
phy template-gui params.py

# Key curation actions:
# - Merge: combine over-split units from the same neuron
# - Split: separate units that Kilosort merged incorrectly
# - Label: mark units as 'good', 'mua' (multi-unit), or 'noise'
# - Save: write curated results to cluster_info.tsv
```

## Why Self-Host Your Spike Sorting Pipeline?

Neural recording datasets are massive — a single Neuropixels probe recording for 2 hours at 30 kHz across 384 channels produces approximately 160 GB of raw data. Uploading this to cloud services is impractical and expensive. Self-hosted pipelines process data locally on dedicated GPU workstations, eliminating transfer bottlenecks entirely.

Beyond data volume, **reproducibility** is a critical concern in systems neuroscience. Spike sorting algorithms evolve rapidly, and minor parameter changes can affect which neurons are detected. Self-hosting the complete pipeline — from raw data through sorting to curation — ensures that every processing step is documented, versioned, and reproducible. SpikeInterface's provenance tracking records every preprocessing and sorting operation, making it possible to exactly reproduce results months later.

For labs working with human or non-human primate data, **regulatory compliance** often requires data to remain on institutional servers. Self-hosted pipelines satisfy IRB (Institutional Review Board) and IACUC requirements by keeping sensitive neural recordings within institutional firewalls.

 The SpikeInterface ecosystem's active development, with monthly releases and a responsive community on GitHub Discussions, means that support for new probe types (Neuropixels 3.0, forthcoming in late 2026) arrives within weeks of hardware release, keeping labs at the cutting edge without vendor lock-in.

For related neuroimaging analysis workflows, see our [EEG and MEG processing guide](../2026-06-10-self-hosted-eeg-meg-neuroimaging-mne-python-fieldtrip-eeglab-guide/) which covers complementary brain recording modalities. If you are working with microscopy-based neuroscience data, our [microscope image analysis comparison](../2026-06-09-self-hosted-microscope-image-analysis-qupath-imagej-cellprofiler/) covers tools for anatomical imaging. For broader data pipeline management, our [bioinformatics workflow platform guide](../2026-06-09-self-hosted-bioinformatics-workflow-platforms-galaxy-nfcore-cwl-guide/) provides scalable workflow orchestration.


## Hardware Considerations and Performance Optimization

The computational demands of spike sorting scale with the number of recording channels, sampling rate, and recording duration. A single Neuropixels 2.0 probe (384 channels at 30 kHz) generates approximately 23 MB/s of raw data. Processing a typical 2-hour recording requires handling 160 GB of data through multiple pipeline stages. Here are the hardware recommendations organized by throughput requirements.

For single-probe processing, a workstation with an NVIDIA RTX 4080 (16GB VRAM), 64GB system RAM, and a fast NVMe SSD (2TB+) provides a balanced configuration. Kilosort 4 running on this hardware processes a 2-hour Neuropixels recording in approximately 3-4 hours, with the GPU handling the template matching and the CPU managing drift correction and post-processing. For multi-probe experiments (4-8 Neuropixels probes simultaneously), scale to a server with dual RTX 4090s or an A6000, 256GB RAM, and RAID-0 NVMe storage for the ~1.3 TB of raw data per session.

For labs without GPU budgets, MountainSort5 and SpykingCircus run on CPU-only systems, albeit at 3-5x slower throughput. A 32-core Threadripper with 128GB RAM can sort a single Neuropixels recording in 12-16 hours using CPU-only sorters, which is viable for overnight batch processing. The SpikeInterface framework automatically selects the appropriate backend based on available hardware, falling back to CPU sorters when GPUs are unavailable. Regardless of hardware, always allocate at least 3x the raw data size for intermediate files — the waveform extraction step alone can produce 200-400 GB of temporary data for long recordings.


## FAQ

### What hardware do I need for spike sorting?

For Kilosort 2.5/4, an NVIDIA GPU with at least 8GB VRAM is recommended (RTX 3070 or better). CPU spike sorters like SpykingCircus or Mountainsort5 can run on CPU-only systems but are significantly slower. A typical workstation with 64GB RAM and an RTX 4080 can process a 2-hour Neuropixels recording in 3-5 hours.

### How do Kilosort 2.5 and 4 differ?

Kilosort 4 (released 2024) is a complete rewrite that runs natively in Python (no MATLAB dependency), handles drift correction more robustly, and produces significantly fewer false-positive units. It also supports both GPU (CUDA) and CPU backends. Kilosort 2.5 remains in wide use for its maturity and extensive validation literature.

### Can SpikeInterface work with my specific recording system?

SpikeInterface supports 30+ recording formats including Neuropixels (SpikeGLX), OpenEphys, Intan, Neuralynx, Blackrock, Plexon, TDT, Axona, and MCS. If your format is not natively supported, the `read_binary()` and `read_nwb()` functions can load from raw binary or NWB files.

### How do I validate spike sorting quality?

Quality metrics computed by SpikeInterface include: SNR (signal-to-noise ratio), ISI violation rate (refractory period violations indicating false positives), amplitude cutoff (fraction of spikes below detection threshold), and presence ratio (temporal consistency). Units passing all four metrics with manual Phy curation are considered validated single units.

### Is MATLAB required for any of these tools?

Kilosort 2.5 and earlier required MATLAB, but Kilosort 4 runs entirely in Python via pykilosort. SpikeInterface and Phy are pure Python. For labs with existing MATLAB pipelines, the MATLAB version of Kilosort 2.5 remains supported but new setups should use Kilosort 4's Python implementation.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Neural Spike Sorting Tools: SpikeInterface vs Kilosort vs Phy",
  "description": "Complete comparison of open-source neural spike sorting tools SpikeInterface, Kilosort, and Phy for self-hosted electrophysiology data analysis, covering installation, pipeline integration, and GPU-accelerated workflow.",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
