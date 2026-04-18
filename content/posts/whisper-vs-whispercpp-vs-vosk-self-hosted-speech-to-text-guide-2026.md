---
title: "Whisper vs whisper.cpp vs Vosk: Best Self-Hosted Speech-to-Text Engines 2026"
date: 2026-04-18
tags: ["comparison", "guide", "self-hosted", "speech-to-text", "transcription"]
draft: false
description: "Compare the top open-source self-hosted speech-to-text engines — OpenAI Whisper, whisper.cpp, and Vosk. Complete Docker deployment guides, performance benchmarks, and accuracy comparisons for running transcription locally in 2026."
---

Running speech-to-text transcription in the cloud means sending your audio data to third-party servers, paying per-minute API fees, and accepting usage caps that can cripple high-volume workflows. Self-hosted transcription engines give you unlimited processing, complete data privacy, and zero per-call costs after the initial hardware investment.

In this guide, we compare the three leading open-source speech recognition engines you can run on your own infrastructure: **OpenAI Whisper**, **whisper.cpp**, and **Vosk**. Each takes a different approach to the transcription problem, and the right choice depends on your accuracy requirements, hardware constraints, and latency needs.

## Why Self-Host Your Speech-to-Text Pipeline

Cloud transcription services like Google Cloud Speech-to-Text, AWS Transcribe, and Azure Speech charge $0.006–$0.024 per minute of audio. At 1,000 hours of monthly transcription, that's $360–$1,440 every month. A self-hosted GPU server costs a one-time hardware investment and then processes unlimited audio for the price of electricity.

Beyond cost, self-hosting gives you:

- **Full data privacy** — audio never leaves your network, essential for healthcare, legal, and financial compliance
- **No rate limits or API quotas** — process 10 files or 10,000 files at the same speed
- **Offline operation** — transcribe on air-gapped systems or during network outages
- **Custom vocabulary and domain tuning** — add industry-specific terms that cloud services don't recognize
- **Predictable latency** — no multi-tenant queueing, consistent response times

For related reading, see our [self-hosted TTS engines guide](../coqui-tts-vs-piper-vs-openvoice-self-hosted-tts-engines-guide-2026/) for the reverse pipeline (text-to-speech), and our [local AI tools comparison](../ollama-vs-lmstudio-vs-localai/) for running other models on-premise.

## OpenAI Whisper — Highest Accuracy, GPU-Optimized

OpenAI released Whisper in September 2022 as an open-source speech recognition model trained on 680,000 hours of multilingual audio. It supports 99 languages and produces remarkably accurate transcripts even with heavy accents, background noise, and technical jargon.

| Metric | Value |
|--------|-------|
| GitHub Stars | 97,987 |
| Language | Python |
| Last Updated | April 2026 |
| Model Sizes | tiny (39M), base (74M), small (244M), medium (769M), large (1.5B) |
| GPU Support | CUDA, MPS (Apple Silicon) |
| License | MIT |

Whisper's architecture uses a sequence-to-sequence Transformer encoder-decoder. The large-v3 model achieves near-human accuracy on most benchmark datasets and handles code-switching between languages naturally. It produces timestamps at the segment level and supports direct translation to English from any supported language.

### Whisper Docker Deployment

The official repository doesn't ship a Docker Compose file, but you can wrap it easily. Here's a production-ready setup using the popular `openai/whisper` pattern with GPU passthrough:

```yaml
version: "3.8"

services:
  whisper:
    image: ghcr.io/openai/whisper:latest
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    volumes:
      - ./audio:/audio:ro
      - ./output:/output
      - ./models:/root/.cache/whisper
    environment:
      - WHISPER_MODEL=large-v3
      - WHISPER_LANGUAGE=en
    command: >
      /audio/input.wav
      --model large-v3
      --output_dir /output
      --output_format srt,vtt,txt
      --language en
      --device cuda
```

For an API server approach, the community-maintained `whisper-server` image exposes a REST endpoint:

```yaml
version: "3.8"

services:
  whisper-api:
    image: onerahmet/openai-whisper-asr-webservice:latest
    ports:
      - "9000:9000"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    volumes:
      - ./models:/root/.cache/whisper
    environment:
      - ASR_MODEL=large-v3
      - ASR_ENGINE=whisper
```

Usage with `curl`:

```bash
curl -X POST http://localhost:9000/asr \
  -F "audio_file=@meeting-recording.wav" \
  -F "output=txt" \
  -F "language=en"
```

**Best for:** Maximum transcription accuracy, multilingual workloads, batch processing of recorded audio, and environments with dedicated GPU hardware.

## whisper.cpp — Lightweight, CPU-First, Edge-Ready

whisper.cpp is a high-performance C/C++ port of OpenAI's Whisper model by Georgi Gerganov. It eliminates the Python and PyTorch dependencies, running inference with a custom GGML tensor library that's optimized for CPU execution and Apple Silicon.

| Metric | Value |
|--------|-------|
| GitHub Stars | 48,735 |
| Language | C/C++ |
| Last Updated | April 2026 |
| Model Sizes | All Whisper sizes (tiny through large), quantized to Q4/Q5/Q8 |
| Hardware | CPU, Apple Silicon, CUDA, Vulkan, SYCL |
| License | MIT |

The killer feature of whisper.cpp is **quantization**. While the original Whisper large model requires ~10 GB of VRAM, a Q4-quantized whisper.cpp model runs in under 3 GB of system RAM on a CPU — making it practical for Raspberry Pi 5, small VPS instances, and edge devices.

The built-in HTTP server (`examples/server`) provides a REST API out of the box, eliminating the need for a separate web framework.

### whisper.cpp Docker Deployment

The project includes official Dockerfiles in `.devops/`. Here's a complete setup with the HTTP server:

```yaml
version: "3.8"

services:
  whisper-cpp:
    build:
      context: .
      dockerfile: |
        FROM ubuntu:22.04 AS build
        WORKDIR /app
        RUN apt-get update && apt-get install -y \
            build-essential wget cmake git ffmpeg libsdl2-dev \
            && rm -rf /var/lib/apt/lists/*
        RUN git clone https://github.com/ggerganov/whisper.cpp . && \
            make -j$(nproc) server
        FROM ubuntu:22.04 AS runtime
        WORKDIR /app
        RUN apt-get update && apt-get install -y \
            ffmpeg libsdl2-dev && rm -rf /var/lib/apt/lists/*
        COPY --from=build /app/build/bin/whisper-server /app/whisper-server
        COPY --from=build /app/models .
        EXPOSE 8080
        ENTRYPOINT ["/app/whisper-server"]
    ports:
      - "8080:8080"
    volumes:
      - ./models:/app/models
      - ./audio:/audio:ro
    command: ["-m", "models/ggml-base.en.bin", "--host", "0.0.0.0", "--port", "8080"]
```

Download a model file before starting the container:

```bash
# Download the base English model (140 MB)
wget -P ./models \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin
```

API usage:

```bash
# Transcribe an audio file
curl -X POST http://localhost:8080/inference \
  -H "Content-Type: multipart/form-data" \
  -F "file=@podcast-ep01.wav" \
  -F "response_format=json"

# Get available endpoints
curl http://localhost:8080 | python3 -m json.tool
```

For GPU acceleration on NVIDIA hardware, use the `main-cuda.Dockerfile` from `.devops/`:

```bash
docker build -f .devops/main-cuda.Dockerfile -t whisper-cpp-cuda .
docker run --gpus all -p 8080:8080 whisper-cpp-cuda \
  -m models/ggml-large-v3-Q4_0.bin --host 0.0.0.0
```

**Best for:** CPU-only servers, edge devices, Apple Silicon Macs, low-memory environments, and applications that need real-time transcription with sub-second latency.

## Vosk — Streaming-First, Ultra-Lightweight

Vosk is an offline speech recognition toolkit built on the Kaldi speech recognition framework. Unlike Whisper's end-to-end neural approach, Vosk uses traditional hybrid HMM-DNN architecture, which makes it dramatically smaller and faster for specific use cases.

| Metric | Value |
|--------|-------|
| GitHub Stars | 14,581 |
| Language | Python/Java/C#/Node (bindings) |
| Last Updated | February 2026 |
| Model Sizes | 40 MB (nano) to 2.1 GB (large) |
| Languages | 20+ languages with dedicated models |
| Hardware | CPU (works on Raspberry Pi Zero) |
| License | Apache 2.0 |

Vosk's standout feature is **real-time streaming recognition**. It processes audio incrementally as it arrives, producing partial transcripts with low latency. This makes it ideal for live captioning, voice commands, and interactive voice response (IVR) systems.

The model sizes range from 40 MB (vosk-model-small) to 2.1 GB (vosk-model-en-us-0.22), with the small models running comfortably on a Raspberry Pi with 512 MB of RAM.

### Vosk Docker Deployment

Vosk provides language-specific bindings but no official Docker Compose file. Here's a production-ready server setup using the community `alphacep/kaldi` image:

```yaml
version: "3.8"

services:
  vosk-server:
    image: alphacep/kaldi-en:latest
    ports:
      - "2700:2700"
    volumes:
      - ./models:/opt/vosk-models
    environment:
      - VOSK_MODEL_PATH=/opt/vosk-models/vosk-model-en-us-0.22
    command: ["python3", "./asr_server.py", "--model", "/opt/vosk-models/vosk-model-en-us-0.22", "--port", "2700"]

  vosk-websocket:
    image: alphacep/kaldi-en:latest
    ports:
      - "2701:2701"
    environment:
      - MODEL_PATH=/opt/vosk-models/vosk-model-en-us-0.22
    command: ["python3", "./asr_server_websocket.py", "--model", "/opt/vosk-models/vosk-model-en-us-0.22", "--port", "2701"]
```

Python client example:

```python
from vosk import Model, KaldiRecognizer
import wave

# Load the model (downloads ~1.6 GB on first run)
model = Model(lang="en-us")

# Open audio file (must be 16kHz mono WAV)
wf = wave.open("recording.wav", "rb")
recognizer = KaldiRecognizer(model, wf.getframerate())

while True:
    data = wf.readframes(4000)
    if len(data) == 0:
        break
    if recognizer.AcceptWaveform(data):
        result = recognizer.Result()
        print(result)  # {"text": "hello world how are you"}
```

WebSocket streaming for real-time transcription:

```python
import asyncio
import websockets
import json

async def transcribe_stream(audio_stream):
    async with websockets.connect("ws://localhost:2701") as ws:
        async for chunk in audio_stream:
            await ws.send(chunk)
            response = json.loads(await ws.recv())
            if "partial" in response:
                print(f"Partial: {response['partial']}")
            elif "text" in response:
                print(f"Final: {response['text']}")
```

**Best for:** Real-time streaming transcription, voice command interfaces, IVR systems, Raspberry Pi and IoT deployments, and applications that need low-latency partial results.

## Head-to-Head Comparison

| Feature | OpenAI Whisper | whisper.cpp | Vosk |
|---------|----------------|-------------|------|
| **Architecture** | Transformer seq2seq | GGML-optimized Transformer | Hybrid HMM-DNN |
| **Languages** | 99 | 99 | 20+ |
| **Accuracy (EN)** | ★★★★★ | ★★★★☆ | ★★★☆☆ |
| **Model Size (large)** | ~10 GB | ~3 GB (Q4) | ~2.1 GB |
| **Smallest Model** | 39 MB (tiny) | 39 MB (tiny Q4) | 40 MB (nano) |
| **GPU Required** | Recommended | Optional (CPU-first) | No |
| **RAM (base model)** | ~1 GB | ~300 MB | ~200 MB |
| **Streaming** | No (batch only) | Limited | Yes (native) |
| **Real-time Factor** | 0.1x–0.5x (GPU) | 0.3x–1x (CPU) | 2x–10x (CPU) |
| **API Server** | Community only | Built-in | Built-in (WebSocket) |
| **Apple Silicon** | MPS (good) | Native (excellent) | Yes |
| **Punctuation** | Automatic | Automatic | Model-dependent |
| **Speaker Diarization** | Via whisper-diarization | No | No |
| **Best Latency** | ~500 ms (GPU) | ~200 ms (CPU) | ~50 ms (CPU) |

### Choosing the Right Engine

**Use OpenAI Whisper when:**
- Transcription accuracy is your top priority
- You have NVIDIA GPU hardware available
- Processing recorded audio in batch (not real-time)
- You need 99-language support with high quality
- You want automatic punctuation and capitalization

**Use whisper.cpp when:**
- You're running on CPU-only hardware
- Memory is constrained (under 4 GB available)
- You need Apple Silicon optimization
- You want a single binary with no Python dependencies
- Edge deployment on resource-limited devices

**Use Vosk when:**
- Real-time streaming is required (live captioning, voice commands)
- You need sub-100 ms partial result latency
- Deploying on Raspberry Pi or microcontrollers
- Your language list is limited to 20 common languages
- You need WebSocket-based incremental results

## Deployment Tips for Production

### Reverse Proxy with TLS

Put any of these engines behind a reverse proxy for HTTPS termination and rate limiting:

```nginx
server {
    listen 443 ssl http2;
    server_name stt.example.com;

    ssl_certificate     /etc/letsencrypt/live/stt.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/stt.example.com/privkey.pem;

    client_max_body_size 100M;  # Allow large audio uploads

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;  # Long-running transcription
    }
}
```

### Audio Format Conversion

All three engines expect 16 kHz mono WAV for optimal results. Use `ffmpeg` to preprocess:

```bash
# Convert any audio to the expected format
ffmpeg -i input.mp3 -ar 16000 -ac 1 -c:a pcm_s16le output.wav

# Extract audio from video
ffmpeg -i meeting.mp4 -ar 16000 -ac 1 -c:a pcm_s16le audio.wav

# Batch convert a directory
for f in *.mp3; do
    ffmpeg -i "$f" -ar 16000 -ac 1 -c:a pcm_s16le "${f%.mp3}.wav"
done
```

### Scaling with Multiple Workers

For high-throughput scenarios, run multiple containers behind a load balancer:

```yaml
version: "3.8"

services:
  whisper-1:
    image: onerahmet/openai-whisper-asr-webservice:latest
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - ASR_MODEL=base

  whisper-2:
    image: onerahmet/openai-whisper-asr-webservice:latest
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - ASR_MODEL=base

  nginx-lb:
    image: nginx:alpine
    ports:
      - "9000:9000"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - whisper-1
      - whisper-2
```

## FAQ

### Which speech-to-text engine is most accurate?

OpenAI Whisper (large-v3 model) achieves the highest accuracy across all benchmark datasets, with word error rates below 3% on clean English speech. whisper.cpp matches Whisper's accuracy since it runs the same model weights in a different runtime. Vosk trails behind at 5–8% WER on the same benchmarks but excels at real-time performance where the others can't compete.

### Can I run Whisper on a CPU without a GPU?

Yes, but performance is limited. Whisper's base model runs at roughly 0.1x real-time on a modern CPU (10 seconds of audio takes 100 seconds to process). For CPU-only deployments, whisper.cpp is the better choice — its quantized base model runs at 0.5–1x real-time on a 4-core CPU, making it practical for batch transcription.

### How much disk space do the models require?

Whisper models range from 39 MB (tiny) to 10 GB (large-v3). whisper.cpp's quantized models are smaller: the large-v3 Q4_0 fits in ~3 GB. Vosk's largest English model is 2.1 GB, while the smallest (vosk-model-small-en-us) is just 40 MB. For most self-hosted setups, the base or small models provide the best accuracy-to-size tradeoff.

### Do these engines support speaker diarization (identifying who said what)?

None of the three engines include built-in speaker diarization. For Whisper, you can use the community `whisper-diarization` project which combines Whisper transcription with pyannote.audio for speaker separation. whisper.cpp and Vosk require a separate diarization pipeline. If you need multi-speaker transcripts, plan to run a diarization model as a post-processing step.

### What audio formats are supported?

Whisper and whisper.cpp accept any format that FFmpeg can decode (MP3, WAV, FLAC, OGG, M4A, etc.) since they call FFmpeg internally. Vosk requires 16 kHz mono PCM WAV input. If your source audio is in another format, convert it with `ffmpeg -i input.mp3 -ar 16000 -ac 1 -c:a pcm_s16le output.wav` before feeding it to Vosk.

### Can these tools transcribe audio in multiple languages simultaneously?

Whisper and whisper.cpp support automatic language detection when you set `--language auto` — they'll detect and transcribe in any of their 99 supported languages, including code-switched audio. Vosk requires you to load a language-specific model and cannot switch languages at runtime. If you need multilingual support with Vosk, you'd need to run separate model instances and route audio to the correct one.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Whisper vs whisper.cpp vs Vosk: Best Self-Hosted Speech-to-Text Engines 2026",
  "description": "Compare the top open-source self-hosted speech-to-text engines — OpenAI Whisper, whisper.cpp, and Vosk. Complete Docker deployment guides, performance benchmarks, and accuracy comparisons for running transcription locally in 2026.",
  "datePublished": "2026-04-18",
  "dateModified": "2026-04-18",
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
