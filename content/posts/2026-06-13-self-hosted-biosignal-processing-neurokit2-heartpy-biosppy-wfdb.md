---
title: "Self-Hosted Biosignal Processing: NeuroKit2 vs HeartPy vs BioSPPy vs WFDB Python"
date: "2026-06-13"
tags: ["biosignal-processing", "ecg-analysis", "physiological-signals", "health-analytics", "research-tools", "python"]
draft: false
---

## Introduction

Biosignal processing — the analysis of physiological signals like ECG (electrocardiogram), PPG (photoplethysmogram), EDA (electrodermal activity), and EMG (electromyography) — is central to health monitoring, wearable device development, and biomedical research. From detecting cardiac arrhythmias to measuring stress responses through skin conductance, these signals carry rich information about human physiology.

Running biosignal analysis on your own infrastructure gives you complete control over sensitive health data while enabling batch processing of large datasets without cloud service costs. Whether you're building a health monitoring dashboard for your smartwatch data, analyzing clinical ECG recordings, or developing research-grade signal processing pipelines, Python's open-source ecosystem provides mature, well-documented tools.

In this guide, we compare four leading Python libraries for biosignal processing: **NeuroKit2**, **HeartPy**, **BioSPPy**, and **WFDB Python**. Each addresses different aspects of the biosignal processing pipeline, from raw waveform analysis to feature extraction and clinical database access.

## Comparison Table

| Feature | NeuroKit2 | HeartPy | BioSPPy | WFDB Python |
|---------|-----------|---------|---------|-------------|
| **GitHub Stars** | 2,257 | 1,126 | 645 | 836 |
| **Signal Types** | ECG, PPG, EDA, EMG, EEG, RSP, EOG | ECG, PPG | ECG, EEG, EMG, EDA | ECG (PhysioNet) |
| **R-Peak Detection** | Multiple algorithms | Native algorithm | Hamilton, Christov | gqrs, xqrs |
| **HRV Analysis** | Comprehensive | Comprehensive | Time/frequency domain | Via PhysioNet |
| **Respiratory Analysis** | Yes | No | Via ECG-derived | Limited |
| **EDA/GSR Processing** | Yes | No | Yes | No |
| **GUI Available** | No (Jupyter) | No (Jupyter) | No (Jupyter) | Lightwave GUI |
| **PhysioNet Access** | Partial | No | No | Full API |
| **Last Updated** | March 2026 | December 2025 | August 2022 | March 2026 |
| **License** | MIT | MIT | BSD-3-Clause | MIT |

## Self-Hosted Installation

### NeuroKit2 Setup

NeuroKit2 is the most comprehensive biosignal processing library available in Python. It supports 8+ signal types with preprocessing, analysis, and visualization:

```bash
# Install NeuroKit2
pip install neurokit2

# With optional dependencies for advanced features
pip install neurokit2[full]
```

Basic usage — process a 30-second ECG recording and extract heart rate variability metrics:

```python
import neurokit2 as nk
import numpy as np

# Generate or load ECG signal
ecg_signal = nk.ecg_simulate(duration=30, sampling_rate=500, heart_rate=70)

# Full processing pipeline: cleaning, R-peak detection, HRV
signals, info = nk.ecg_process(ecg_signal, sampling_rate=500)

# Extract HRV metrics
hrv_indices = nk.hrv_time(signals, sampling_rate=500)
print(f"Mean HR: {hrv_indices['HRV_MeanNN']:.1f} ms")
print(f"SDNN: {hrv_indices['HRV_SDNN']:.1f} ms")
print(f"RMSSD: {hrv_indices['HRV_RMSSD']:.1f} ms")

# Also process EDA, EMG, PPG signals
eda_signal = nk.eda_simulate(duration=30, sampling_rate=500)
eda_signals, eda_info = nk.eda_process(eda_signal, sampling_rate=500)
```

### HeartPy Installation

HeartPy focuses specifically on heart rate analysis from PPG and ECG signals, with excellent handling of noisy wearable data:

```bash
pip install heartpy
```

```python
import heartpy as hp
import numpy as np

# Load PPG or ECG data
data = hp.get_data('data.csv')

# Process with automatic filtering
wd, m = hp.process(data, sample_rate=100.0)

# Access computed metrics
print(f"BPM: {m['bpm']:.1f}")
print(f"IBI: {m['ibi']:.1f} ms")
print(f"SDNN: {m['sdnn']:.1f} ms")
print(f"Breathing Rate: {m['breathingrate']:.2f}")

# Plot analysis
hp.plotter(wd, m)
```

### BioSPPy Installation

BioSPPy provides a modular approach to biosignal processing with a focus on ECG and EEG analysis:

```bash
pip install biosppy
```

```python
from biosppy.signals import ecg
from biosppy.signals import eda
import numpy as np

# ECG processing
signal = np.loadtxt('ecg_recording.csv')
out = ecg.ecg(signal=signal, sampling_rate=1000., show=False)

print(f"Filtered signal: {out['filtered'].shape}")
print(f"R-peaks at samples: {out['rpeaks'][:10]}")
print(f"Heart rate: {out['heart_rate'][:10]}")

# EDA processing
eda_out = eda.eda(signal=eda_signal, sampling_rate=100., show=False)
print(f"Tonic component: {eda_out['tonic'].shape}")
print(f"Phasic component: {eda_out['phasic'].shape}")
```

### WFDB Python Installation

WFDB Python provides direct access to PhysioNet's extensive database of physiological recordings, plus local waveform analysis:

```bash
pip install wfdb
```

```python
import wfdb

# Download a PhysioNet record
record = wfdb.rdrecord('mitdb/100', sampto=15000)

# Access signals and metadata
print(f"Signal shape: {record.p_signal.shape}")
print(f"Sampling rate: {record.fs} Hz")
print(f"Signal names: {record.sig_name}")

# Download annotations for QRS detection
annotation = wfdb.rdann('mitdb/100', 'atr', sampto=15000)
print(f"QRS annotations: {len(annotation.sample)} beats")

# Plot waveform with annotations
wfdb.plot_wfdb(record=record, annotation=annotation, title='MIT-BIH Record 100')
```

## Building a Self-Hosted Biosignal Dashboard

For health monitoring applications, you can build a centralized biosignal analysis server that processes data from multiple wearable devices or clinical recordings:

```bash
# Create a Python service for batch biosignal processing
mkdir -p /opt/biosignal-server
cd /opt/biosignal-server
python3 -m venv venv
source venv/bin/activate
pip install neurokit2 heartpy biosppy wfdb flask pandas
```

```python
# server.py — Self-hosted biosignal analysis API
from flask import Flask, request, jsonify
import neurokit2 as nk
import heartpy as hp
import numpy as np

app = Flask(__name__)

@app.route('/analyze/ecg', methods=['POST'])
def analyze_ecg():
    data = request.json
    signal = np.array(data['signal'])
    sr = data.get('sampling_rate', 500)
    
    # Process with NeuroKit2
    signals, info = nk.ecg_process(signal, sampling_rate=sr)
    hrv = nk.hrv_time(signals, sampling_rate=sr)
    
    # Process with HeartPy for cross-validation
    wd, m = hp.process(signal, sample_rate=sr)
    
    return jsonify({
        'neurokit2_hrv': {
            'mean_nn': float(hrv['HRV_MeanNN'].iloc[0]),
            'sdnn': float(hrv['HRV_SDNN'].iloc[0]),
            'rmssd': float(hrv['HRV_RMSSD'].iloc[0]),
        },
        'heartpy': {
            'bpm': float(m['bpm']),
            'sdnn': float(m['sdnn']),
        },
        'r_peaks_detected': len(info['ECG']['R_Peaks'])
    })

@app.route('/analyze/eda', methods=['POST'])
def analyze_eda():
    data = request.json
    signal = np.array(data['signal'])
    sr = data.get('sampling_rate', 500)
    
    signals, info = nk.eda_process(signal, sampling_rate=sr)
    
    return jsonify({
        'tonic_mean': float(signals['EDA_Tonic'].mean()),
        'phasic_peaks': int(info.get('SCR_Peaks_N', 0)),
        'phasic_amplitude_mean': float(signals['EDA_Phasic'].mean()),
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)
```

Run the server:

```bash
# Run behind nginx reverse proxy
gunicorn -w 4 -b 127.0.0.1:5050 server:app

# Nginx config
# /etc/nginx/sites-available/biosignal
server {
    listen 80;
    server_name biosignal.lab.internal;
    
    location / {
        proxy_pass http://127.0.0.1:5050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Choosing the Right Tool for Your Workflow

**NeuroKit2** is the Swiss Army knife — it processes the widest variety of signal types (ECG, PPG, EDA, EMG, EEG, RSP, EOG) with a consistent API. If you're building a multi-modal biosignal pipeline, start here. Its `_process()` functions handle cleaning, peak detection, and feature extraction in one call.

**HeartPy** excels at heart rate analysis from wearable PPG sensors. Its signal quality assessment and automatic filtering handle the noise and motion artifacts common in consumer wearables better than general-purpose libraries. If your data comes from Fitbit, Apple Watch, or similar devices, HeartPy's preprocessing is tuned for that.

**BioSPPy** provides lower-level access to individual processing steps (filtering, R-peak detection, heart rate computation) with clean, modular code. It's a good choice when you need to customize the processing pipeline beyond what NeuroKit2's high-level API provides.

**WFDB Python** is essential if you work with PhysioNet databases or clinical ECG formats (MIT-BIH, AHA). Its record-reading API handles dozens of waveform formats and annotation types that other libraries don't support.

## Why Self-Host Biosignal Analysis?

Health data is among the most sensitive personal information you can collect. Running biosignal analysis on your own infrastructure ensures that ECG recordings, sleep data, and stress metrics never leave your control. This is particularly important for clinical research where HIPAA or GDPR compliance requires data to remain within institutional boundaries.

Self-hosting also enables real-time analysis loops. For closed-loop neurofeedback or biofeedback applications, the round-trip latency to a cloud service makes real-time intervention impossible. A local processing server can analyze incoming data in under 100ms and trigger responses immediately.

Beyond compliance, running your own biosignal server gives you audit trails and reproducibility that cloud services don't provide. You know exactly which version of each algorithm processed your data, and you can re-run analyses when methods improve.

For broader health monitoring infrastructure, see our guide on [fitness workout tracking platforms](../2026-06-03-self-hosted-fitness-workout-tracking-wger-workout-tracker-fittrackee/). For medical imaging data management, check out our [DICOM PACS medical imaging guide](../2026-06-04-self-hosted-dicom-pacs-medical-imaging-orthanc-dcm4che-ohif-dicoogle-guide/). For healthcare interoperability, see our [FHIR HL7 healthcare data guide](../2026-06-04-self-hosted-fhir-hl7-healthcare-interoperability-hapi-microsoft-blaze-ibm-guide/).

## FAQ

### What's the difference between ECG and PPG signals?

ECG (electrocardiogram) measures the heart's electrical activity through electrodes on the skin. It provides the gold standard for heart rhythm analysis and QRS complex detection. PPG (photoplethysmogram) uses light to measure blood volume changes and is common in wrist-worn wearables. PPG is more susceptible to motion artifacts but doesn't require chest electrodes. HeartPy handles both; NeuroKit2 provides dedicated processing pipelines for each.

### Can I use these tools with Apple Watch or Fitbit data?

Yes. Export your wearable data to CSV or JSON format, then load it into any of these libraries. HeartPy has specific preprocessing routines for consumer wearable PPG signals that handle the lower sampling rates and higher noise levels typical of wrist-worn devices. NeuroKit2's `ppg_process()` function also works with wearable PPG data.

### How do I handle noisy signals from wearable devices?

All four libraries include filtering and artifact removal. NeuroKit2 applies a 0.5-45 Hz bandpass filter by default on ECG signals. HeartPy uses an automatic masking approach that detects and interpolates over noisy segments. BioSPPy applies Butterworth filtering with configurable cutoffs. For extremely noisy data, consider applying wavelet denoising or template matching after the library's built-in filtering.

### What file formats are supported for input data?

All libraries accept NumPy arrays and CSV files. WFDB Python additionally reads WFDB-format records, EDF (European Data Format), and MIT-BIH annotation files. If you have clinical ECG data in HL7 aECG, DICOM waveform, or ISHNE formats, you may need to convert to CSV first using format-specific parsers.

### Can I combine multiple libraries in one pipeline?

Yes, and this is a common pattern. Use WFDB Python to load PhysioNet records, NeuroKit2 for preprocessing and signal cleaning, HeartPy for HRV metrics on noisy wearable data, and BioSPPy when you need lower-level control over individual processing steps. Since all four libraries operate on NumPy arrays, data flows seamlessly between them.

---

**💡 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Biosignal Processing: NeuroKit2 vs HeartPy vs BioSPPy vs WFDB Python",
  "description": "Compare four open-source Python libraries for biosignal processing: NeuroKit2, HeartPy, BioSPPy, and WFDB Python. Self-hosted ECG, PPG, EDA, and EMG analysis with installation guides and API server setup.",
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
