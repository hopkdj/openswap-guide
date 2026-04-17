---
title: "Best Self-Hosted Chatbot Frameworks 2026: Rasa vs Botpress vs Langflow"
date: 2026-04-17T07:02:00Z
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Compare the top open-source chatbot frameworks you can self-host in 2026. Detailed guide covering Rasa, Botpress, and Langflow with Docker setup, feature comparison, and deployment best practices."
---

Building a chatbot doesn't mean handing your conversation data to a third-party SaaS platform. Whether you're creating a customer support assistant, an internal knowledge bot, or an automated workflow agent, self-hosting your chatbot framework gives you complete control over your data, model training, and deployment pipeline.

In 2026, the open-source chatbot ecosystem has matured significantly. Three frameworks stand out for different use cases: **Rasa** for production-grade NLP pipelines, **Botpress** for visual bot building with an integrated studio, and **Langflow** for rapidly prototyping conversational AI flows using large language models. This guide compares all three, walks through Docker deployment for each, and helps you pick the right tool for your project.

## Why Self-Host Your Chatbot Framework

Running a chatbot on a SaaS platform means every conversation, every user message, and every intent classification flows through someone else's servers. Self-hosting solves several problems at once:

- **Data sovereignty**: Customer conversations and user data never leave your infrastructure. This is critical for healthcare, finance, and enterprise use cases where data residency requirements apply.
- **Cost predictability**: SaaS chatbot platforms charge per message, per conversation, or per active user. At scale, those costs add up fast. A self-hosted solution has fixed infrastructure costs regardless of volume.
- **Custom model training**: Self-hosted frameworks let you train NLU models on your own domain data without sharing it with an external API. Your bot gets smarter on your vocabulary, your products, and your users' language patterns — privately.
- **No vendor lock-in**: When your chatbot logic, training data, and conversation flows live in your own repositories, you're never trapped by a platform's pricing changes or feature deprecations.
- **Offline operation**: Some environments — industrial facilities, government networks, or air-gapped systems — need chatbots that work without any external API calls. Self-hosted frameworks deliver this.

## Rasa: The Production-Grade NLP Pipeline

[Rasa](https://rasa.com) (formerly Rasa Open Source) is the most widely adopted open-source chatbot framework. It separates Natural Language Understanding (NLU) from dialogue management, giving you granular control over how your bot processes messages and maintains conversation state.

### Architecture

Rasa's architecture has two main components:

1. **Rasa NLU**: Classifies user intent and extracts entities from messages. Supports transformer-based pipelines, spaCy integration, and custom components.
2. **Rasa Core**: Manages dialogue state using rule-based and machine learning policies. The Rules Policy handles deterministic flows (like "if user asks for password reset, collect email"), while the TED Policy learns from conversation stories to handle ambiguous paths.

### Key Features

- Pipeline-based NLU with configurable components (tokenizer, featurizer, classifier)
- Story-driven dialogue management with interactive learning
- Form-based slot filling for multi-turn data collection
- REST and socket.io connectors for channel integration
- Rasa X (separate product) for conversation review and training data management
- Extensive documentation and large community

### Docker Deployment

```yaml
# docker-compose.yml for Rasa
version: "3.8"

services:
  rasa:
    image: rasa/rasa:3.6.20-full
    ports:
      - "5005:5005"
    volumes:
      - ./rasa-project:/app
    working_dir: /app
    command: >
      rasa run
      --enable-api
      --cors "*"
      --debug
    depends_on:
      - rasa-db

  rasa-db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: rasa
      POSTGRES_PASSWORD: rasa_secret
      POSTGRES_DB: rasa_tracker
    volumes:
      - rasa-db-data:/var/lib/postgresql/data

  rasa-action-server:
    image: rasa/rasa-sdk:3.6.2
    ports:
      - "5055:5055"
    volumes:
      - ./actions:/app/actions
    working_dir: /app/actions

volumes:
  rasa-db-data:
```

### Initial Setup

```bash
# Create a new Rasa project
docker compose run --rm rasa rasa init --no-prompt

# Train the NLU model
docker compose run --rm rasa rasa train

# Test with curl
curl -X POST http://localhost:5005/webhooks/rest/webhook \
  -H "Content-Type: application/json" \
  -d '{"sender": "test_user", "message": "Hello!"}'
```

### Rasa's NLU Pipeline Configuration

```yaml
# config.yml
recipe: default.v1
language: en

pipeline:
  - name: WhitespaceTokenizer
  - name: RegexFeaturizer
  - name: LexicalSyntacticFeaturizer
  - name: CountVectorsFeaturizer
  - name: CountVectorsFeaturizer
    analyzer: char_wb
    min_ngram: 1
    max_ngram: 4
  - name: DIETClassifier
    epochs: 100
    constrain_similarities: true
  - name: EntitySynonymMapper
  - name: ResponseSelector
    epochs: 100

policies:
  - name: RulePolicy
    core_fallback_threshold: 0.3
    core_fallback_action_name: "action_default_fallback"
  - name: TEDPolicy
    max_history: 5
    epochs: 100
  - name: MemoizationPolicy
    max_history: 5
```

### When to Choose Rasa

Rasa is the right choice when you need a production-ready chatbot with fine-grained control over NLU, custom entity extraction, and complex dialogue management. It's ideal for teams with ML engineers who want to optimize every layer of the pipeline. The trade-off is a steeper learning curve — you write YAML configurations, Python action code, and manage training data manually.

## Botpress: The Visual Bot Builder

[Botpress](https://botpress.com) takes a different approach. Instead of writing configuration files, you build conversation flows visually using a drag-and-drop studio. Botpress v12 (the open-source edition) provides a complete development environment with a web-based editor, built-in NLU, and channel connectors.

### Architecture

Botpress organizes bot logic into **flows** — visual state machines where each node represents a message, question, or action. The built-in NLU engine handles intent classification and entity extraction, while the **Botpress Studio** provides a real-time preview and debugging interface.

### Key Features

- Visual flow editor with drag-and-drop node connections
- Built-in NLU with intent training through the UI
- Code editor for custom JavaScript actions
- Pre-built channel connectors (Webchat, Telegram, Slack, Messenger)
- Conversation management dashboard
- Multi-language support with built-in translation workflows
- Knowledge base integration for RAG-style Q&A bots

### Docker Deployment

```yaml
# docker-compose.yml for Botpress v12
version: "3.8"

services:
  botpress:
    image: botpress/server:v12_31_8
    ports:
      - "3000:3000"
      - "3001:3001"
    environment:
      - DATABASE_URL=postgres://botpress:bp_secret@bp-db:5432/botpress
      - EXTERNAL_URL=http://localhost:3000
      - CLUSTER_ENABLED=false
      - PRO_ENABLED=false
    volumes:
      - botpress-data:/botpress/data
    depends_on:
      - bp-db

  bp-db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: botpress
      POSTGRES_PASSWORD: bp_secret
      POSTGRES_DB: botpress
    volumes:
      - bp-db-data:/var/lib/postgresql/data

  bp-redis:
    image: redis:7-alpine
    volumes:
      - bp-redis-data:/data

volumes:
  botpress-data:
  bp-db-data:
  bp-redis-data:
```

### Getting Started

After starting the Docker compose stack, open `http://localhost:3000` in your browser. The initial setup wizard will prompt you to create an admin account and your first bot.

```bash
# Start the stack
docker compose up -d

# Watch the logs
docker compose logs -f botpress

# Botpress is ready when you see:
# "Botpress Server ready on port 3000"
```

### Building Your First Flow

1. Open the Botpress Studio at `http://localhost:3000/admin`
2. Create a new bot from the template gallery
3. In the Flow Editor, drag a **Text** node onto the canvas
4. Connect it to a **Question** node that captures user input
5. Add an NLU intent trigger to route different responses
6. Test in the built-in Emulator panel

For programmatic bot management, Botpress exposes a REST API:

```bash
# Create a conversation via API
curl -X POST http://localhost:3001/api/v1/bots/my-bot/converse/default \
  -H "Content-Type: application/json" \
  -d '{
    "type": "text",
    "text": "What are your business hours?"
  }'
```

### When to Choose Botpress

Botpress shines when you need a visual development environment that non-technical team members can use. If your workflow involves content writers, product managers, or support leads building and maintaining conversation flows, the visual editor dramatically reduces friction. The trade-off is less flexibility at the NLU level compared to Rasa's configurable pipelines.

## Langflow: The LLM-Powered Flow Designer

[Langflow](https://langflow.org) is the newest entrant and represents a different paradigm entirely. Instead of training custom NLU models, Langflow lets you build conversational flows by chaining together LLM calls, vector stores, prompt templates, and tools — all visually. It's essentially a visual interface for LangChain, the popular Python framework for building applications on top of large language models.

### Architecture

Langflow provides a drag-and-drop canvas where each node represents a LangChain component: an LLM wrapper, a prompt template, a vector store retriever, a memory buffer, or an output parser. You connect nodes with wires to define data flow, and Langflow generates the underlying LangChain code automatically.

### Key Features

- Visual flow builder for LangChain components
- Drag-and-drop prompt engineering with live preview
- Built-in support for open-weight LLMs (via Ollama, llama.cpp, vLLM)
- Vector store integration (Chroma, Qdrant, Milvus, FAISS)
- Memory types for multi-turn context (conversation buffer, summary, window)
- API endpoint generation for each flow
- Flow export/import and version management
- Chat playground for real-time testing

### Docker Deployment

```yaml
# docker-compose.yml for Langflow
version: "3.8"

services:
  langflow:
    image: langflowai/langflow:v1.2.0
    ports:
      - "7860:7860"
    environment:
      - LANGFLOW_DATABASE_URL=sqlite:///./langflow.db
      - LANGFLOW_SECRET_KEY=change-me-in-production
      - LANGFLOW_AUTO_LOGIN=False
    volumes:
      - langflow-data:/app/langflow
      - ./flows:/app/flows

  # Optional: Local LLM via Ollama for full self-hosted stack
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  langflow-data:
  ollama-data:
```

### Building a Self-Hosted Conversational Bot

```bash
# Start Langflow and Ollama
docker compose up -d

# Pull a model for local inference
docker exec ollama ollama pull llama3.1:8b

# Open Langflow
# Navigate to http://localhost:7860
```

Once Langflow is running, you can build a conversational flow by dragging these components onto the canvas:

1. **Chat Input** — receives user messages
2. **Prompt Template** — defines the system prompt and message format
3. **Ollama LLM** — connects to your local Ollama instance at `http://ollama:11434`
4. **Conversation Buffer Memory** — stores the last N messages for context
5. **Chat Output** — returns the LLM response

You can extend this with **Retrieval QA** nodes that pull context from a vector store, or **Tool** nodes that let the LLM call external APIs, run code, or query databases — all without leaving the visual editor.

### Exporting a Flow as Code

One of Langflow's most powerful features is the ability to export any flow as Python code:

```python
# Exported from Langflow — a complete RAG chatbot
from langflow.load import run_flow_from_json
from langchain_ollama import ChatOllama

result = run_flow_from_json(
    flow_path="./flows/customer-support-flow.json",
    input_value="How do I reset my password?",
)
print(result.get("text"))
```

### When to Choose Langflow

Langflow is ideal when you want to build conversational AI powered by LLMs without writing code. It's perfect for rapid prototyping, RAG-based knowledge bots, and teams that want the flexibility of LangChain with a visual interface. Because it works with local LLMs through Ollama, you can run the entire stack — UI, orchestration, and inference — without any external API calls.

## Feature Comparison

| Feature | Rasa | Botpress v12 | Langflow |
|---------|------|-------------|----------|
| **Primary Paradigm** | NLU pipeline + dialogue policies | Visual flow editor + NLU | Visual LLM flow builder |
| **UI/Studio** | None (CLI only; Rasa X is separate) | Built-in web studio | Built-in web studio |
| **NLU Approach** | Custom trained models (DIET, spaCy) | Built-in intent classifier | LLM-based (via Ollama, OpenAI, etc.) |
| **Training Data** | YAML stories, NLU examples | UI-based intent training | No training needed (prompt-based) |
| **Programming Language** | Python | JavaScript/TypeScript | Python (LangChain) |
| **Channel Connectors** | REST, Socket.io, custom | Webchat, Telegram, Slack, Messenger | REST API (custom integrations via code) |
| **Memory/Context** | Dialogue state + slots | Flow variables + session storage | Conversation buffer, summary, vector stores |
| **Multi-Language** | Yes (per-pipeline config) | Yes (built-in translation) | Yes (depends on LLM) |
| **Docker Image Size** | ~2.5 GB (full) | ~800 MB | ~1.2 GB |
| **Resource Requirements** | 4 GB RAM min, GPU optional for training | 2 GB RAM min | 2 GB RAM + 8 GB for local LLM |
| **Learning Curve** | Steep (ML concepts required) | Moderate (visual but has JS for actions) | Moderate (familiarity with LLM concepts helps) |
| **Best For** | Production NLP pipelines, custom entities | Team-based bot building, quick deployment | LLM-powered chatbots, RAG, prototyping |
| **License** | Apache 2.0 | AGPLv3 | MIT |

## Choosing the Right Framework

The decision comes down to your team's skills and your bot's requirements:

**Choose Rasa if** you're building a high-volume production chatbot that needs precise intent classification, custom entity extraction, and deterministic dialogue flows. A healthcare intake bot that extracts patient IDs, appointment dates, and symptom descriptions from free text is a perfect Rasa use case. The pipeline architecture lets you optimize every step, and the policy ensemble handles edge cases gracefully.

**Choose Botpress if** a cross-functional team needs to build and maintain conversation flows together. The visual editor means content creators can write responses, product managers can define flows, and developers can add custom JavaScript for complex logic. An e-commerce support bot with product recommendations, order tracking, and FAQ answers is well-suited for Botpress.

**Choose Langflow if** you want to build an LLM-powered conversational agent with retrieval-augmented generation. If your use case involves answering questions from a knowledge base, summarizing documents, or generating responses from unstructured data, Langflow's visual LangChain builder lets you iterate quickly. Pair it with a local Ollama instance for a fully self-hosted stack that never sends data externally.

## Deployment Best Practices for Self-Hosted Chatbots

Regardless of which framework you choose, follow these practices for production deployments:

### Reverse Proxy with TLS

```nginx
# /etc/nginx/sites-available/chatbot.example.com
server {
    listen 443 ssl http2;
    server_name chatbot.example.com;

    ssl_certificate /etc/letsencrypt/live/chatbot.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/chatbot.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5005;  # Rasa
        # proxy_pass http://127.0.0.1:3000;  # Botpress
        # proxy_pass http://127.0.0.1:7860;  # Langflow
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /socket.io/ {
        proxy_pass http://127.0.0.1:5005;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Health Checks and Monitoring

```yaml
# Add health checks to your docker-compose.yml
services:
  rasa:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5005/"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
```

### Backup Strategy

```bash
#!/bin/bash
# backup-chatbot.sh — daily backup script

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="/opt/backups/chatbot/${TIMESTAMP}"
mkdir -p "${BACKUP_DIR}"

# Backup Rasa project files
cp -r /opt/rasa-project "${BACKUP_DIR}/rasa-project"

# Backup Botpress data
docker compose exec -T botpress tar czf - /botpress/data \
  > "${BACKUP_DIR}/botpress-data.tar.gz"

# Backup Langflow flows and database
cp /opt/langflow/flows/*.json "${BACKUP_DIR}/"
cp /opt/langflow/langflow.db "${BACKUP_DIR}/"

# Backup PostgreSQL databases
docker compose exec -T rasa-db pg_dump -U rasa rasa_tracker \
  > "${BACKUP_DIR}/rasa-tracker.sql"

# Clean backups older than 30 days
find /opt/backups/chatbot -maxdepth 1 -mtime +30 -exec rm -rf {} \;

echo "Backup complete: ${BACKUP_DIR}"
```

### Rate Limiting

```nginx
# Rate limit incoming requests to prevent abuse
limit_req_zone $binary_remote_addr zone=chatbot:10m rate=30r/m;

server {
    location / {
        limit_req zone=chatbot burst=5 nodelay;
        proxy_pass http://127.0.0.1:5005;
    }
}
```

## Conclusion

Self-hosting a chatbot framework in 2026 is more accessible than ever. Rasa gives you the deepest NLP control for production systems. Botpress provides the most collaborative visual environment for team-based development. Langflow opens the door to LLM-powered conversational AI with zero training data required.

All three can run entirely on your own infrastructure with Docker, and all three support the integrations needed to reach users across web, messaging apps, and custom channels. The key is matching the framework to your team's skills and your bot's complexity — then deploying it with proper TLS, monitoring, and backup practices from day one.
