---
title: "Self-Hosted Acoustic Monitoring: NoiseModelling vs OpenSoundscape vs PAMGuard"
date: "2026-06-09"
tags: ["environmental-monitoring", "acoustics", "soundscape-ecology", "noise-monitoring", "bioacoustics", "open-science", "scientific-computing"]
draft: false
---

## Introduction

Sound is a fundamental data stream for environmental monitoring — urban noise pollution affects public health, bioacoustic recordings reveal ecosystem biodiversity, and underwater soundscapes track marine mammal populations. Open source acoustic analysis platforms enable researchers, city planners, and conservationists to process massive audio datasets without proprietary software licenses.

In this guide, we compare three specialized open source platforms for different acoustic monitoring domains: **NoiseModelling** (urban and environmental noise mapping), **OpenSoundscape** (terrestrial bioacoustics and soundscape ecology), and **PAMGuard** (passive acoustic monitoring for marine mammals). Each serves a distinct scientific community with different deployment models and analysis workflows.

## Comparison Table

| Feature | NoiseModelling | OpenSoundscape | PAMGuard |
|---------|---------------|----------------|----------|
| **Primary Domain** | Urban/environmental noise mapping | Terrestrial bioacoustics | Marine mammal acoustics |
| **GitHub Stars** | 223⭐ | 214⭐ | 66⭐ |
| **Language** | Java + Python | Python | Java |
| **Input Formats** | WAV, GeoJSON, shapefiles | WAV, FLAC, MP3 | WAV, AIF, X3 (proprietary) |
| **Real-time Processing** | No (post-processing) | Via command-line scheduler | Yes (real-time detection) |
| **GIS Integration** | Full (NoiseCapture, QGIS) | Limited (GeoJSON export) | GPS track integration |
| **Web Interface** | WPS/OGC services | None (Python API + CLI) | Real-time viewer + spectrogram |
| **Docker Support** | Docker image available | Conda/Pip install | Native installer packages |
| **Detection Algorithms** | CNOSSOS-EU, NMPB-08 | CNN classifiers (BirdNET, Perch) | Click detector, whistle detector, matched filter |
| **Multi-Channel** | Grid-based computation | Multi-file processing | Multi-hydrophone arrays |

## NoiseModelling: Urban Noise Mapping for Smart Cities

NoiseModelling is an open source platform implementing the European CNOSSOS-EU (Common Noise Assessment Methods) standard for strategic noise mapping. It processes traffic, industrial, and environmental noise sources to generate noise exposure maps required by the EU Environmental Noise Directive.

### Docker Deployment

```yaml
version: '3.8'
services:
  noisemodelling:
    image: ifsttar/noisemodelling:latest
    container_name: noisemodelling
    ports:
      - "8080:8080"
    volumes:
      - /data/noise/input:/data/input
      - /data/noise/output:/data/output
      - /data/noise/config:/data/config
    environment:
      JAVA_OPTS: "-Xmx32G"
      WPS_SERVER: "true"
    restart: unless-stopped
```

### Running a Noise Map Computation

NoiseModelling provides a WPS (Web Processing Service) interface as well as a Groovy scripting API. Here's a command-line example for generating a road traffic noise map:

```bash
# Generate noise map from traffic data
docker exec noisemodelling java -Xmx16G -jar /opt/noisemodelling/wps_scripts/traffic_noise.jar \
  --input-buildings /data/input/buildings.shp \
  --input-roads /data/input/roads.shp \
  --input-dem /data/input/dem.tif \
  --input-population /data/input/population.shp \
  --output-dir /data/output/ \
  --noise-indicator Lden \
  --grid-resolution 10.0 \
  --receivers-height 4.0 \
  --max-propagation-distance 800
```

### Groovy Script for Custom Noise Analysis

```groovy
import org.noisemodelling.analysis.Analysis
import org.noisemodelling.runner.Runner

def runner = new Runner()
    .setInputPath("/data/input/")
    .setOutputPath("/data/output/")
    .setBuildings("buildings.geojson")
    .setSources("traffic_sources.geojson")
    .setDEM("dem.tif")
    .setGridStep(5.0)

// Run CNOSSOS-EU road noise computation
def result = runner.runTrafficNoise(
    method: "CNOSSOS-EU",
    roadSurface: "DAC_0/11",
    vehicleDistribution: [
        light: 0.85,
        medium: 0.10, 
        heavy: 0.05
    ],
    averageSpeed: 50,
    dailyTraffic: 15000
)

Analysis.exportNoiseMap(result, "/data/output/lden_noise_map.tif")
```

## OpenSoundscape: Bioacoustics for Conservation Science

OpenSoundscape from the Kitzes Lab at University of Pittsburgh provides a Python-based framework for analyzing terrestrial bioacoustic recordings. It's designed for conservation biologists studying bird, frog, bat, and insect populations through automated soundscape analysis.

### Installation and Setup

```bash
# Clone and install OpenSoundscape
git clone https://github.com/kitzeslab/opensoundscape.git
cd opensoundscape
pip install -e .

# Install with deep learning support
pip install opensoundscape[tensorflow]
```

### Automated Species Detection Pipeline

```python
from opensoundscape import Audio, SpectrogramPreprocessor
from opensoundscape.ml import CNN
from pathlib import Path

# Load a pre-trained BirdNET classifier
model = CNN.from_pretrained('birdnet', 'BirdNET_GLOBAL_6K_V2.4')
preprocessor = SpectrogramPreprocessor(sample_duration=3.0)

# Process a directory of audio files
audio_dir = Path("/data/field_recordings/")
results = []

for audio_file in audio_dir.glob("*.wav"):
    audio = Audio.from_file(audio_file, sample_rate=48000)
    
    # Generate spectrograms and run classification
    specs = preprocessor.process(audio)
    predictions = model.predict(specs)
    
    # Get species detections above confidence threshold
    detections = predictions[predictions['confidence'] > 0.7]
    results.append({
        'file': audio_file.name,
        'detections': detections.to_dict()
    })

# Export results as CSV for GIS mapping
import pandas as pd
pd.DataFrame(results).to_csv("/data/output/species_detections.csv")
```

## PAMGuard: Real-Time Marine Mammal Monitoring

PAMGuard (Passive Acoustic Monitoring Guard) is the standard platform for real-time detection, classification, and localization of marine mammals during research surveys and industrial operations. It's used worldwide for mitigating the impact of seismic surveys, offshore wind construction, and naval operations on protected marine species.

### Self-Hosted Deployment for Data Review

PAMGuard is typically deployed as a desktop application but supports a viewer mode for post-processing and data review on centralized servers:

```bash
# Install PAMGuard on a Linux server
wget https://github.com/PAMGuard/PAMGuard/releases/download/v2.02.10/PAMGuard_2_02_10_linux.sh
chmod +x PAMGuard_2_02_10_linux.sh
./PAMGuard_2_02_10_linux.sh --mode unattended --prefix /opt/pamguard

# Run in viewer mode for headless data processing
/opt/pamguard/bin/PAMGuard \
  --mode viewer \
  --input /data/pamguard/recordings/ \
  --psf /data/pamguard/setup.psf \
  --output /data/pamguard/results/
```

### Detector Configuration for Dolphin Whistles

PAMGuard uses a modular processing architecture where detector modules are configured in a PSF (PAMGuard Settings File). Here's an example whistle detector configuration:

```groovy
// PAMGuard module configuration
WhistleDetector {
    name = "Whistle Detector"
    channelMap = [0, 1]
    fftLength = 1024
    fftHop = 512
    sampleRate = 192000
    
    whistleConnect {
        minLength = 10       // minimum whistle length in FFT frames
        maxCrossLength = 2   // max missing crossings for connection
        minFrequency = 5000  // 5 kHz minimum
        maxFrequency = 40000 // 40 kHz maximum
    }
    
    frequencySweep {
        minSweep = 0.0
        maxSweep = 0.15     // frequency sweep per time bin
    }
}

// Click detector for odontocete echolocation
ClickDetector {
    name = "Click Detector"
    channelMap = [0, 1]
    sampleRate = 500000
    threshold = 12.0        // dB above noise floor
    minClickSeparation = 0.5 // milliseconds
    longFilterAlpha = 0.0001
    shortFilterAlpha = 0.01
}
```

## Why Self-Host Your Acoustic Monitoring?

Environmental acoustic data is inherently location-sensitive — noise maps contain infrastructure details, bioacoustic recordings reveal endangered species locations, and marine mammal detections trigger regulatory compliance actions. Self-hosting ensures this data remains under your control with appropriate access restrictions.

Data volumes in acoustic monitoring are substantial: a single hydrophone array generates 500 GB per day, and a city-wide noise sensor network produces continuous streaming data. Self-hosted infrastructure avoids the egress costs and bandwidth limitations of cloud platforms. For context on related environmental monitoring approaches, see our [wildlife camera and bird monitoring guide](../2026-06-05-self-hosted-wildlife-camera-bird-monitoring-birdnet-pi-naturewatch-motioneye/) and our [seismic monitoring comparison](../2026-06-06-self-hosted-seismic-monitoring-raspberry-shake-openeew-seiscomp-guide/).

The regulatory landscape also favors self-hosting. EU noise mapping submissions under Directive 2002/49/EC require auditable processing pipelines — self-hosted NoiseModelling provides full provenance. Similarly, marine mammal monitoring for US MMPA and UK JNCC compliance requires detector configurations that can be validated and locked — features PAMGuard's PSF file system provides.

For labs integrating multiple data streams, our [weather station software guide](../2026-05-04-self-hosted-weather-station-software-weewx-meteobridge-weather34-guide/) covers complementary meteorological monitoring that can be correlated with acoustic data for comprehensive environmental analysis.

## Hardware Requirements and Sensor Deployment

Deploying a comprehensive acoustic monitoring infrastructure involves sensors in the field and processing servers in the lab. Each acoustic monitoring domain has distinct hardware requirements:

For urban noise monitoring, a city-wide deployment typically uses 20-50 noise monitoring terminals at strategic locations. Each terminal runs a Raspberry Pi or similar SBC with a Class 1 sound level meter connected via USB, streaming data to a central NoiseModelling server over 4G/WiFi. A medium city of 500,000 population requires approximately 4-8 hours of computation on a 32-core server with 64 GB RAM to generate a full Lden noise map at 10m grid resolution.

Bioacoustics field deployments commonly use 10-50 autonomous recording units like AudioMoth or Swift across study areas of 10 to 10,000 hectares. Each unit records 1-4 weeks of continuous audio, generating about 8 GB per day per unit. After retrieval, OpenSoundscape processes this data in batches — a 4-week, 50-unit deployment generates 11 TB of raw audio. Processing with BirdNET CNN classification on a server with an RTX 3060 GPU handles roughly 300 hours of audio per hour.

Marine passive acoustic monitoring operates at industrial scale. Offshore energy projects deploy hydrophone arrays at depths of 50-200m, streaming real-time audio via fiber optic cables. A single 8-hydrophone array sampling at 192 kHz generates approximately 500 GB per day. PAMGuard processes this in real-time on dedicated DSP hardware — simultaneously running click detectors for porpoises, whistle detectors for delphinids, and matched filters for baleen whale calls, all within the latency budget required for operational mitigation decisions.

## FAQ

### How accurate is automated species detection compared to manual annotation?

OpenSoundscape's BirdNET classifier achieves 85-90% precision for common North American and European bird species at confidence thresholds above 0.7. PAMGuard's whistle detectors are routinely used as primary detection methods in regulatory contexts, validated against manual analysis with >95% recall for delphinid whistles. However, rare species and complex soundscapes still benefit from human verification of automated detections.

### Can I build a city-wide noise monitoring network with these tools?

Yes. NoiseModelling processes noise data from distributed measurement networks. Pair it with a mobile measurement app like NoiseCapture (Android) to collect citizen science data. The WPS interface allows municipalities to run periodic noise map updates via cron jobs, ingesting new traffic counts and sensor data automatically.

### What hardware do I need for a self-hosted acoustic monitoring server?

For batch processing: a server with 32-64 GB RAM and 8+ CPU cores handles most workloads. NoiseModelling benefits from high single-thread performance for CNOSSOS-EU computations. OpenSoundscape with GPU acceleration (NVIDIA RTX 3060+) speeds up CNN classification 10-50x. PAMGuard requires minimal resources in viewer mode (<8 GB RAM) but real-time processing with multi-channel arrays needs dedicated DSP hardware.

### How do these tools handle long-duration recordings (weeks to months)?

OpenSoundscape processes audio in configurable segments (default 3 seconds) and can handle multi-month recordings through chunked processing. PAMGuard supports continuous real-time monitoring with data managed in its binary storage system with database indexing for fast retrieval. NoiseModelling works with aggregated noise indicators rather than raw audio, making it efficient for long-term trend analysis.

### Are there integration options with existing GIS and data management systems?

NoiseModelling exports to GeoTIFF, GeoJSON, and Shapefile for direct QGIS and ArcGIS integration. OpenSoundscape exports detection results as CSV with GPS timestamps for GIS mapping. PAMGuard's database backend can be queried programmatically and its localization results export to KMZ for Google Earth visualization. All three tools support standard scientific data formats for integration with data repositories and electronic lab notebooks.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Acoustic Monitoring: NoiseModelling vs OpenSoundscape vs PAMGuard",
  "description": "Compare three specialized open source platforms for acoustic monitoring — NoiseModelling (urban noise mapping), OpenSoundscape (terrestrial bioacoustics), and PAMGuard (marine mammal passive acoustic monitoring) — covering Docker deployment, real-time detection, and regulatory compliance workflows.",
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
      "url": "https://hopkdj.github.io/openswap-guide/logo.png"
    }
  }
}
</script>

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
