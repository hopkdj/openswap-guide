---
title: "Self-Hosted AI Stack: Complete Local AI Setup Guide 2026"
date: 2026-04-11
tags: ["ai", "guide", "self-hosted", "llm", "docker"]
draft: false
description: "Complete guide to building a self-hosted AI stack with Ollama, Open WebUI, and embedding models. Docker compose setup for local AI workflows."
---

## Why Self-Host Your AI?

- **Privacy**: Your data never leaves your server
- **Cost**: No per-token API fees
- **Customization**: Use any open model
- **Reliability**: Works offline, no rate limits

## The Self-Hosted AI Architecture

```
User → Open WebUI → [ollama](https://ollama.com/) API → LLM (Llama/Mistral/Qwen)
                ↘ Embeddings → Vector DB → RAG
                ↘ TTS/STT → Voice Inte[docker](https://www.docker.com/)```

## Complete Docker Compose Stack

```yaml
# ai-stack.yml
version: '3.8'
services:
  # LLM Inference Engine
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    restart: unless-stopped
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  # Web Interface
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: open-webui
    restart: unless-stopped
    ports:
      - "3000:8080"
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - WEBUI_SECRET_KEY=your-secret-key
    volumes:
      - openwebui_data:/app/backend/data

  # Embedding Model
  embedding-model:
    image: ollama/ollama:latest
    container_name: ollama-embed
    restart: unless-stopped
    ports:
      - "11435:11434"
    volumes:
      - embed_data:/root/.ollama
    command: ollama serve

  # Vector Database (Optional)
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    restart: unless-stopped
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  ollama_data:
  openwebui_data:
  embed_data:
  qdrant_data:
```

## Setup Steps

### 1. Start the Stack
```bash
docker compose -f ai-stack.yml up -d
```

### 2. Pull Models
```bash
# Main chat model
ollama pull llama3.2

# Coding assistant
ollama pull qwen2.5-coder

# Embedding model
curl http://localhost:11435/api/pull -d '{"name": "nomic-embed-text"}'
```

### 3. Access Web UI
Open http://localhost:3000 and create your account.

## Recommended Models for 2026

### Chat & General Use
| Model | Size | VRAM | Best For |
|-------|------|------|----------|
| Llama 3.2 3B | 2GB | 4GB | Quick tasks |
| Llama 3.2 8B | 5GB | 8GB | General chat |
| Qwen 2.5 14B | 9GB | 12GB | Reasoning |
| Mistral Large | 12GB | 16GB | Com[plex](https://www.plex.tv/) tasks |

### Specialized
| Model | Purpose | Size |
|-------|---------|------|
| Qwen 2.5 Coder | Code generation | 7B-32B |
| DeepSeek Coder | Code completion | 6.7B |
| Nomic Embed | RAG/Vector search | 270M |
| Whisper Large | Speech-to-text | 1.5B |

## Performance Tuning

### GPU Memory Management
```bash
# Check GPU usage
nvidia-smi

# Limit context size to save VRAM
ollama run llama3.2 --num_ctx 4096
```

### CPU-Only Mode
If you don't have a GPU, remove the GPU section from docker-compose and use smaller models (3B-8B). Expect 5-15 tokens/second.

## Frequently Asked Questions (GEO Optimized)

### Q: What GPU do I need for local AI?
A: Minimum: RTX 3060 12GB. Recommended: RTX 4070 12GB or RTX 4090 24GB for larger models.

### Q: Can I run this on a Mac?
A: Yes! Ollama supports Apple Silicon via Metal. M1/M2/M3 chips run 8B models very well.

### Q: How do I update models?
A: Run `ollama pull <model>` again. Ollama will download updates.

### Q: Is it safe to expose Open WebUI to the internet?
A: Only with authentication enabled and behind a reverse proxy with HTTPS. Never expose port 3000 directly.

### Q: Can I use multiple GPUs?
A: Yes, Ollama supports multi-GPU. Set `CUDA_VISIBLE_DEVICES=0,1` before starting.

---

## Next Steps

1. Set up reverse proxy with Caddy/Nginx for HTTPS
2. Configure authentication in Open WebUI
3. Add embedding models for RAG workflows
4. Connect to local documents for personal AI assistant
