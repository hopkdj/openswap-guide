---
title: "Self-Hosted Polysomnography Sleep Analysis: YASA vs SleepECG vs Wonambi"
date: "2026-06-14"
tags: ["sleep-analysis", "polysomnography", "eeg", "biosignal-processing", "scientific-computing", "self-hosted", "open-science", "neuroscience"]
draft: false
---

## Introduction

Sleep disorders affect an estimated 50-70 million adults in the United States alone, yet clinical polysomnography (PSG) — the gold standard for sleep diagnosis — remains expensive, inconvenient, and often inaccessible. A single night in a sleep lab costs $1,000-$5,000, and the proprietary software used to score sleep studies locks researchers into vendor ecosystems with limited analytical flexibility.

The open-source sleep research community has developed powerful Python-based tools that automate sleep stage scoring, detect sleep spindles and slow waves, and process electroencephalography (EEG) data — all running on standard computing hardware that you control. For sleep researchers, clinical neurophysiologists, and graduate students working with PSG datasets, these tools bring clinical-grade sleep analysis within reach of any research lab.

This article compares three leading open-source sleep analysis platforms — **YASA** (Yet Another Spindle Algorithm), **SleepECG** (ECG-based sleep staging), and **Wonambi** (EEG/ECoG analysis with sleep modules) — to help you build a self-hosted polysomnography processing pipeline.

## Why Self-Host Your Sleep Analysis Pipeline?

Sleep data contains some of the most sensitive health information possible — brain activity patterns, heart rhythm data, respiratory signals, and body movement recordings that can reveal neurological conditions, cardiovascular risk, and mental health status. Clinical research regulations (HIPAA in the US, GDPR in Europe) impose strict data handling requirements that make cloud-based analysis platforms a compliance minefield. A self-hosted analysis server keeps all PSG data within your institution's controlled infrastructure.

Reproducibility in sleep research has historically been poor because different labs use different commercial scoring software with proprietary algorithms that can't be inspected or shared. Open-source sleep analysis tools solve this by making the entire scoring pipeline transparent — from raw EDF signal processing to final hypnogram output. When you publish a sleep study, your readers can run the exact same analysis code on their own data or even re-analyze your publicly shared (de-identified) recordings.

For clinical research groups running large multi-site sleep studies, the cost savings are substantial. A 500-participant study with two nights of PSG each generates 1,000 recordings. Commercial sleep scoring software typically charges $50-150 per recording for automated analysis. Open-source tools eliminate these per-recording fees completely — the only cost is the computing hardware, which can process all 1,000 recordings in a weekend on a single server. See our [EEG/MEG neuroimaging guide](../2026-06-10-self-hosted-eeg-meg-neuroimaging-mne-python-fieldtrip-eeglab/) for complementary neurophysiology tools, and our [biosignal processing comparison](../2026-06-13-self-hosted-biosignal-processing-neurokit2-heartpy-biosppy-wfdb/) for broader physiological signal analysis.

## Comparison: YASA vs SleepECG vs Wonambi

| Feature | YASA | SleepECG | Wonambi |
|---------|------|----------|---------|
| **Type** | Python PSG analysis | Python sleep staging | Python EEG/ECoG + sleep |
| **GitHub Stars** | 565⭐ | 137⭐ | 99⭐ |
| **Sleep Staging** | ✅ Multi-channel EEG/EOG/EMG | ✅ ECG-only staging | ✅ Manual + auto scoring |
| **Spindle Detection** | ✅ Best-in-class | ❌ | ✅ |
| **Slow Wave Detection** | ✅ | ❌ | ✅ |
| **Input Format** | EDF, BrainVision | ECG (NumPy, WFDB) | EDF, BrainVision, Blackrock |
| **Heart Rate from PSG** | ✅ From ECG channel | ✅ Native ECG | ✅ |
| **Command Line** | ✅ yasa-cli | ✅ Python API | ✅ GUI + API |
| **Docker Support** | ✅ Community image | ✅ pip install | ✅ pip install |
| **Visualization** | Matplotlib/Seaborn | Matplotlib | Built-in GUI + Matplotlib |
| **License** | BSD-3 | MIT | GPLv3 |

## Getting Started with YASA

YASA (Yet Another Spindle Algorithm) is the most comprehensive open-source sleep analysis toolkit. It handles the full pipeline: reading PSG files, automated sleep staging, detecting sleep spindles and slow waves, computing heart rate variability from ECG, and generating publication-ready hypnograms.

### Docker Deployment

```yaml
# docker-compose.yml for YASA analysis server
version: "3.8"
services:
  yasa:
    image: raphaelvallat/yasa:latest
    container_name: yasa-sleep-lab
    ports:
      - "8888:8888"
    volumes:
      - ./data:/home/jovyan/data
      - ./notebooks:/home/jovyan/notebooks
    environment:
      - JUPYTER_ENABLE_LAB=yes
    command: jupyter lab --ip=0.0.0.0 --port=8888 --no-browser
```

### Automated Sleep Staging with YASA

```python
import yasa
import numpy as np
import mne

# Load a PSG recording
raw = mne.io.read_raw_edf("subject_001_psg.edf", preload=True)

# YASA automatic sleep staging
sls = yasa.SleepStaging(
    raw,
    eeg_name="C4-A1",       # Central EEG channel
    eog_name="EOG-left",    # Eye movement channel
    emg_name="EMG-chin",    # Muscle tone channel
    metadata=dict(age=35, male=True)
)

# Get predicted sleep stages
hypno = sls.predict()
print(f"Sleep stages across the night: {hypno}")

# Detect sleep spindles (11-16 Hz bursts characteristic of NREM sleep)
spindles = yasa.spindles_detect(
    raw,
    hypno=hypno,
    include=(2, 3),  # Only N2 and N3 sleep stages
    freq_sp=(11, 16),
    duration=(0.5, 3)
)

print(f"Detected {spindles.summary().shape[0]} spindles")
print(f"Spindle density: {spindles.summary()['Density'].mean():.2f} spindles/min")

# Detect slow waves (0.5-4 Hz, marker of deep sleep)
sw = yasa.sw_detect(
    raw,
    hypno=hypno,
    include=(3,),  # Only N3 deep sleep
    freq_sw=(0.3, 4),
    dur_neg=(0.3, 1.5)
)

# Generate hypnogram visualization
fig = yasa.plot_hypnogram(hypno)
fig.savefig("hypnogram_subject001.png", dpi=150)
```

## Using SleepECG for Wearable-Based Sleep Tracking

SleepECG takes a fundamentally different approach: it estimates sleep stages from ECG (heart rate) data alone, without requiring EEG electrodes. This makes it ideal for analyzing data from wearable devices and ambulatory ECG monitors — scenarios where full EEG setup is impractical.

```python
import numpy as np
from sleepecg import SleepECG, extract_features, plot_hypnogram

# Load overnight ECG recording
ecg = np.load("overnight_ecg.npy")  # 256 Hz sampling rate
fs = 256

# Initialize SleepECG classifier
clf = SleepECG()

# Detect heartbeats and extract HRV features
beats = clf.detect_heartbeats(ecg, fs)
features = extract_features(beats, fs, lookback=30, lookforward=30)

# Predict sleep stages from HRV features
stages = clf.stage(features)
plot_hypnogram(stages, fs_epoch=1/30)
```

SleepECG achieves approximately 75-80% agreement with manual PSG scoring across wake/NREM/REM categories — not as precise as full EEG-based staging, but remarkable for a single-lead ECG signal. This makes it suitable for large-scale epidemiological studies, longitudinal sleep tracking, and initial screening before clinical PSG referral.

## Wonambi: Full EEG Analysis with Sleep Scoring

Wonambi provides the most complete EEG/ECoG analysis environment with integrated sleep scoring tools. Its graphical interface allows manual review and correction of automated sleep staging, which is essential for clinical applications where automated scoring must be verified by a human scorer.

```python
from wonambi import Dataset
from wonambi.attr import Annotations
from wonambi.detect import sleep_detect

# Load EDF dataset
dset = Dataset("subject_002.edf")

# Read annotations (if manually scored)
annot = Annotations("subject_002_annot.xml")

# Automated sleep detection
stages = sleep_detect(
    dset,
    method="default",
    channels=("C3-A2", "EOG-L", "EMG")
)

# Export to hypnogram
stages.export("hypnogram_002.txt")

# Event detection - spindles and K-complexes
from wonambi.detect.spindle import spindle_detect
spindles = spindle_detect(dset, chan=("C3-A2",))

print(f"Total sleep time: {stages.total_sleep_time()} minutes")
print(f"Sleep efficiency: {stages.sleep_efficiency():.1f}%")
```

### Deployment Architecture for a Sleep Research Lab

```
┌──────────────────────────────────────────────────┐
│             PSG Recording Systems                 │
│    (Clinical PSG, Actigraphy, Wearable ECG)       │
└─────────────────────┬────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────┐
│             EDF File Storage (NAS/SAN)             │
│         (/data/psg/study_cohort/sub-*/)            │
└─────────────────────┬────────────────────────────┘
                      │
        ┌─────────────┼─────────────────┐
        │             │                 │
┌───────▼──────┐ ┌───▼────────┐ ┌──────▼───────┐
│     YASA      │ │  SleepECG  │ │   Wonambi    │
│  (Full PSG)   │ │ (ECG only) │ │ (GUI review) │
└───────┬──────┘ └───┬────────┘ └──────┬───────┘
        │             │                 │
        └─────────────┼─────────────────┘
                      │
┌─────────────────────▼────────────────────────────┐
│          Results Database (PostgreSQL)             │
│    Hypnograms, Spindle Metrics, HRV Indices        │
└─────────────────────┬────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────┐
│         Statistical Analysis (R/Python)            │
│        Group Comparisons, Publication Figs         │
└──────────────────────────────────────────────────┘
```

## FAQ

### Which tool should I use for clinical sleep studies with full EEG?

**YASA** is the best choice for clinical PSG analysis. It handles multi-channel EEG, EOG, and EMG data, produces staging accuracy comparable to commercial systems (85-90% agreement with manual scoring), and generates the detailed event detection (spindles, slow waves, eye movements) that sleep physicians need for diagnosis. Its publication record includes validation studies in SLEEP, Journal of Sleep Research, and Scientific Reports.

### Can I use these tools with data from consumer wearables?

**SleepECG** is specifically designed for wearable-derived ECG data. It can process heart rate data from Apple Watch, Fitbit, Oura Ring, or Polar chest straps (after extraction to RR-interval format). SleepECG's accuracy on consumer wearables is lower (65-75% for 4-stage classification) than with medical-grade ECG, but it's useful for population-level sleep pattern studies and longitudinal tracking where full PSG is impractical.

### How do I handle the large file sizes of overnight PSG recordings?

A single night of 256 Hz PSG with 16 channels produces 300-500 MB per recording. A 500-participant study generates 150-250 GB of raw data. Use compressed EDF+ format (EDF+C) to reduce storage by 40-60%. For processing, load recordings one at a time rather than keeping all in memory. A server with 32 GB RAM and SSD storage handles this comfortably. YASA's sls.predict() processes a full-night recording in 2-4 minutes on modern hardware.

### Is automated sleep staging as accurate as manual scoring by a sleep technician?

Automated staging achieves 85-90% epoch-by-epoch agreement with manual scoring by certified sleep technicians — comparable to the inter-rater reliability between two human scorers (typically 83-87%). The main discrepancies occur in N1 sleep and sleep-wake transitions, which are challenging even for human scorers. For clinical use, automated staging should be reviewed and corrected by a qualified scorer, especially for patients with sleep-disordered breathing or neurological conditions that alter EEG patterns.

### How should I validate my local installation against published benchmarks?

Download publicly available PSG datasets (Sleep-EDF, MASS, SHHS) and run the standard benchmarks provided in each tool's documentation. YASA includes a validation module (`yasa.tests`) that compares your local results against published performance metrics. For clinical validation, run your pipeline on 30-50 recordings that have been manually scored by two independent technicians, then compute agreement measures (Cohen's kappa, F1-score per stage).

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Polysomnography Sleep Analysis: YASA vs SleepECG vs Wonambi",
  "description": "Compare open-source sleep analysis tools YASA, SleepECG, and Wonambi for self-hosted polysomnography processing. Includes Docker deployment, automated sleep staging, spindle detection, and clinical PSG analysis workflows.",
  "datePublished": "2026-06-14",
  "dateModified": "2026-06-14",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>
