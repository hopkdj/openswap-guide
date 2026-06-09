---
title: "Self-Hosted Electronics Lab Software: sigrok/PulseView vs Scopy vs EEZ Studio"
date: "2026-06-09"
tags: ["electronics", "test-equipment", "oscilloscope", "signal-analysis", "lab-automation", "hardware-debugging", "open-source-hardware"]
draft: false
---

## Introduction

Every electronics lab — whether a professional R&D facility, a university teaching lab, or a home workbench — relies on test equipment: oscilloscopes, logic analyzers, signal generators, and power supplies. Traditionally, each instrument came with its own proprietary software, creating a fragmented workflow and vendor lock-in. Open source electronics lab software consolidates instrument control, data acquisition, and analysis into unified, extensible platforms.

In this guide, we compare three leading open source platforms for electronics lab instrumentation: **sigrok/PulseView** (multi-instrument data acquisition and signal analysis), **Scopy** (Analog Devices' software-defined instrumentation suite), and **EEZ Studio** (modular test & measurement automation). Each takes a different approach to unifying the electronics workbench.

## Comparison Table

| Feature | sigrok/PulseView | Scopy | EEZ Studio |
|---------|-----------------|-------|------------|
| **Primary Use Case** | Universal data acquisition & signal analysis | ADALM2000 & M2K instrument control | Modular T&M automation & instrument design |
| **GitHub Stars** | 746⭐ | 494⭐ | 1,676⭐ |
| **Language** | C (library) + C++ (GUI) | C++ with QML UI | C++ + JavaScript/Python |
| **Supported Hardware** | 120+ devices (Saleae, DSLogic, Hantek, Rigol, etc.) | ADALM2000, ADALM-Pluto | EEZ BB3, SCPI instruments, DIY modules |
| **Protocol Decoders** | 115+ protocols (I2C, SPI, UART, CAN, USB, etc.) | SPI, I2C, UART, GPIO, Pattern Generator | SCPI-based, user-extensible |
| **Real-time Analysis** | Yes, with protocol decoding | Yes, with FFT and math channels | Yes, with dashboard scripting |
| **Remote Access** | sigrok-cli + TCP bridge | M2K via libm2k network API | WebSocket + REST API |
| **Docker Support** | Headless CLI Docker image | Limited (M2K requires USB) | Yes, for automation servers |
| **Scripting** | Python (libsigrok + sigrok-cli) | Python (libm2k) | JavaScript, Python (SCPI) |
| **License** | GPLv3 | GPLv3 | GPLv3 |

## sigrok/PulseView: The Universal Signal Analysis Platform

sigrok is the most comprehensive open source signal analysis framework, supporting over 120 hardware devices from budget USB logic analyzers ($10) to professional oscilloscopes ($2,000+). Its modular architecture separates hardware drivers, protocol decoders, and visualization into independent libraries.

### Docker Deployment for Automated Testing

Run sigrok in headless mode for continuous integration testing of embedded systems:

```dockerfile
# Dockerfile for sigrok automated testing
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    sigrok-cli \
    sigrok-firmware-fx2lafw \
    python3-libsigrok \
    python3-numpy \
    python3-matplotlib

COPY test_runner.py /opt/test_runner.py
ENTRYPOINT ["python3", "/opt/test_runner.py"]
```

### Automated I2C Bus Verification Script

```python
#!/usr/bin/env python3
"""Automated I2C verification using sigrok"""
import subprocess
import json

def capture_i2c(duration=5):
    """Capture I2C traffic for specified duration"""
    result = subprocess.run([
        "sigrok-cli",
        "-d", "fx2lafw",           # Use FX2-based logic analyzer
        "--config", "samplerate=1MHz",
        "-P", "i2c:scl=0:sda=1",   # I2C decoder on channels 0,1
        "--time", str(duration),
        "-O", "i2c:words=yes",      # Output decoded I2C words
        "--continuous"
    ], capture_output=True, text=True, timeout=duration + 5)
    
    return result.stdout

def verify_device_address(data, expected_addr=0x68):
    """Verify device responds at expected I2C address"""
    for line in data.split('\n'):
        if 'Address' in line and hex(expected_addr) in line:
            return True
    return False

# Main test sequence
i2c_data = capture_i2c(duration=3)
if verify_device_address(i2c_data):
    print("PASS: Device found at expected I2C address")
else:
    print("FAIL: Device not responding on I2C bus")
```

### Protocol Decoding for CAN Bus

sigrok supports 115+ protocol decoders. Here's how to decode CAN bus traffic from a logic analyzer capture:

```bash
# Capture and decode CAN bus with 500kbps bitrate
sigrok-cli -d fx2lafw --config samplerate=4MHz \
  -P can:can_rx=0:can_tx=1:bitrate=500000 \
  --time 10 -O can:format=json \
  > can_output.json

# Parse the output for specific CAN IDs
python3 -c "
import json
with open('can_output.json') as f:
    data = json.load(f)
for frame in data:
    if frame.get('can_id') == 0x7E8:  # Engine RPM PID
        print(f'CAN ID 0x7E8: Data={frame["data"]}')
"
```

## Scopy: Software-Defined Instrumentation

Scopy is Analog Devices' open source instrumentation software designed for their ADALM2000 (M2K) active learning module. It transforms a $279 USB device into a full suite of instruments: oscilloscope, spectrum analyzer, network analyzer, signal generator, logic analyzer, pattern generator, and digital I/O.

### Installation

```bash
# Install Scopy on Debian/Ubuntu
wget -q -O - https://raw.githubusercontent.com/analogdevicesinc/scopy/master/CI/appveyor/install_ubuntu_deps.sh | bash

# Build from source
git clone https://github.com/analogdevicesinc/scopy.git
cd scopy
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)
sudo cmake --install build
```

### M2K Remote Access via libm2k

For headless server deployment, use the libm2k Python API to control the ADALM2000 remotely:

```python
import libm2k
import numpy as np

# Connect to M2K over USB (or network with m2k-fw proxy)
ctx = libm2k.m2kOpen()
if ctx is None:
    raise RuntimeError("M2K not found")

# Configure analog input (oscilloscope)
ain = ctx.getAnalogIn()
ain.setSampleRate(100000000)  # 100 MS/s
ain.setRange(0, libm2k.PLUS_MINUS_5V)
ain.enableChannel(0, True)

# Configure signal generator
aout = ctx.getAnalogOut()
aout.setSampleRate(0, 75000000)  # 75 MS/s
aout.setSampleRate(1, 75000000)
aout.enableChannel(0, True)

# Generate a 1 kHz sine wave with FSK modulation
buffer_size = 8192
samples = np.sin(2 * np.pi * 0.2 * np.arange(buffer_size) / buffer_size)
aout.push(0, samples.tolist())

# Capture data
data = ain.getSamples(8192)
print(f"Captured {len(data[0])} samples, Vpp: {np.max(data[0]) - np.min(data[0]):.3f}V")

# Run FFT for spectrum analysis
fft = np.abs(np.fft.fft(data[0]))
freqs = np.fft.fftfreq(len(data[0]), 1/100e6)
print(f"Peak frequency: {freqs[np.argmax(fft[:len(fft)//2])]:.0f} Hz")

libm2k.contextClose(ctx)
```

## EEZ Studio: Modular Test & Measurement Automation

EEZ Studio from Envox provides a visual low-code environment for building test and measurement dashboards. Unlike sigrok and Scopy (which focus on signal analysis), EEZ Studio emphasizes instrument control, automation, and custom dashboard creation — making it ideal for production test systems.

### Self-Hosted Automation Server

```yaml
version: '3.8'
services:
  eez-studio-server:
    image: eez-open/studio:latest
    container_name: eez-automation
    ports:
      - "8081:8081"    # WebSocket dashboard
      - "8082:8082"    # REST API
    volumes:
      - /data/eez/projects:/opt/eez-studio/projects
      - /data/eez/instruments:/opt/eez-studio/instruments
      - /data/eez/logs:/opt/eez-studio/logs
    environment:
      EEZ_SERVER_MODE: "true"
      EEZ_INSTRUMENT_PATH: "/opt/eez-studio/instruments"
    devices:
      - "/dev/usbtmc0:/dev/usbtmc0"  # USB-TMC instrument
      - "/dev/ttyUSB0:/dev/ttyUSB0"   # Serial instrument
    restart: unless-stopped
```

### Dashboard Automation Script

EEZ Studio dashboards are defined in a project format with embedded JavaScript for automation:

```javascript
// EEZ Studio dashboard automation script
// Monitor power supply and log efficiency during battery charge test

var measurements = [];
var testRunning = false;

function startTest() {
    testRunning = true;
    dashboard.setControlValue("status_led", "yellow");
    
    // Configure power supply via SCPI
    instrument.execute("PSU1", "*RST");
    instrument.execute("PSU1", "VOLT 4.2");
    instrument.execute("PSU1", "CURR 1.0");
    instrument.execute("PSU1", "OUTP ON");
    
    // Start periodic measurement
    setInterval(measureEfficiency, 5000); // every 5 seconds
}

function measureEfficiency() {
    if (!testRunning) return;
    
    var vin = instrument.query("PSU1", "MEAS:VOLT?");
    var iin = instrument.query("PSU1", "MEAS:CURR?");
    var vout = instrument.query("DMM1", "MEAS:VOLT:DC?");
    var iout = instrument.query("DMM2", "MEAS:CURR:DC?");
    
    var pin = parseFloat(vin) * parseFloat(iin);
    var pout = parseFloat(vout) * parseFloat(iout);
    var efficiency = (pout / pin) * 100;
    
    measurements.push({
        time: Date.now(),
        vin: parseFloat(vin),
        vout: parseFloat(vout),
        iout: parseFloat(iout),
        efficiency: efficiency
    });
    
    dashboard.setControlValue("efficiency_gauge", efficiency);
    dashboard.setControlValue("power_chart", measurements);
    
    // Auto-stop when current drops below termination threshold
    if (parseFloat(iout) < 0.05) {
        stopTest();
    }
}

function stopTest() {
    instrument.execute("PSU1", "OUTP OFF");
    testRunning = false;
    dashboard.setControlValue("status_led", "green");
    
    // Export results
    dashboard.exportCSV("/output/battery_test_" + 
        new Date().toISOString().slice(0,10) + ".csv", measurements);
}
```

## Why Self-Host Your Electronics Lab Software?

Electronics lab software controls physical instruments that can damage hardware or create safety hazards if misconfigured. Self-hosting ensures the control chain is fully under your control — no cloud dependencies mean no latency issues when toggling power supplies or stopping a thermal runaway test. For related instrument control topics, see our [RF signal analysis guide](../2026-06-06-self-hosted-rf-signal-analysis-urh-sigdigger-inspectrum-guide/) and our [SCADA systems comparison](../2026-05-02-self-hosted-scada-systems-fuxa-scada-lts-rapidscada-guide/).

Intellectual property protection is another driver. Automated test sequences for proprietary embedded systems contain sensitive design information. Self-hosted EEZ Studio dashboards and sigrok protocol decoders stay within your network, never exposing test vectors to external services. This is particularly critical for defense contractors, medical device manufacturers, and semiconductor validation labs.

For labs building comprehensive testing infrastructure, our [thermal camera integration guide](../2026-06-07-self-hosted-thermal-camera-ir-imaging-mlx90640-amg8833-flir-lepton-guide/) shows how thermal imaging can complement electronic testing for identifying hot spots and thermal anomalies during validation runs.

## Building an Automated Electronics Test Pipeline

Creating an end-to-end automated test system requires orchestrating multiple instruments, stimulus generation, response capture, and pass/fail analysis. A hybrid approach combines the strengths of all three platforms: EEZ Studio handles power supply sequencing and relay control via SCPI, sigrok-cli performs bus-level protocol verification (I2C, SPI, CAN), and Scopy/libm2k provides high-speed analog measurements when an ADALM2000 is available.

A typical embedded system validation sequence flows through five stages. First, EEZ Studio powers up the DUT with a controlled voltage ramp and monitors inrush current. Second, sigrok captures the boot sequence on I2C and confirms the device acknowledges its address within 100ms. Third, Scopy generates a test waveform and measures the analog front-end response for gain and noise floor. Fourth, EEZ Studio logs all measurements to InfluxDB for trend analysis and statistical process control. Finally, the pipeline posts pass/fail results to a CI/CD dashboard with failure screenshots captured via VNC.

The entire pipeline runs in Docker containers with USB device passthrough, enabling reproducible test environments across development and production floors. Each test step has configurable timeouts and retry logic, making it suitable for regression testing of firmware updates, manufacturing validation, and incoming quality inspection for electronic components.

## FAQ

### Can sigrok replace a professional oscilloscope?

sigrok is a software framework, not hardware. With a high-quality USB oscilloscope (e.g., PicoScope or Rigol DS1000Z series), sigrok provides advanced analysis comparable to vendor software — protocol decoding, measurements, and export. However, it doesn't match the real-time responsiveness of dedicated oscilloscope firmware for very high-speed debugging (>200 MHz). For logic analysis, sigrok + a $10 FX2LP board equals or exceeds $500+ Saleae analyzers for protocol decoding.

### Do I need the ADALM2000 to use Scopy?

Scopy is designed for the ADALM2000 and won't work with other hardware without modification. However, the libm2k library provides a Python API that can control the M2K from any application. For generic instrument control, sigrok or EEZ Studio offer wider hardware compatibility.

### How do I automate regression testing of embedded systems?

Combine sigrok-cli for signal capture and protocol verification with EEZ Studio for power sequencing and instrument control. A Python orchestration script can: (1) power-cycle the DUT via SCPI, (2) capture boot sequence I2C/SPI traffic with sigrok, (3) verify protocol responses, and (4) log results. This setup runs in CI/CD pipelines via Docker containers.

### Are these tools suitable for university teaching labs?

Yes. Scopy is explicitly designed for education with the ADALM2000, providing an oscilloscope, spectrum analyzer, and signal generator in one device ($279). sigrok's broad hardware support lets students use affordable logic analyzers ($10-50). EEZ Studio's visual dashboard builder helps students create measurement GUIs without coding.

### Can I integrate these with Python-based data analysis workflows?

All three support Python integration. sigrok provides the libsigrok Python bindings for direct hardware control and data capture. Scopy's libm2k has a full Python API for remote instrument control. EEZ Studio exports data in CSV/JSON and supports Python SCPI scripting. Captured data flows directly into NumPy, SciPy, and Jupyter notebooks for advanced analysis.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Electronics Lab Software: sigrok/PulseView vs Scopy vs EEZ Studio",
  "description": "Compare three leading open source platforms for electronics lab instrumentation — sigrok/PulseView (multi-device signal analysis), Scopy (Analog Devices M2K suite), and EEZ Studio (modular T&M automation) — covering Docker deployment, protocol decoding, and automated testing pipelines.",
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
