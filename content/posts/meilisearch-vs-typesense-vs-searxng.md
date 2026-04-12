---
title: "Meilisearch vs Typesense vs SearXNG: Best Self-Hosted Search Engines 2026"
date: 2026-04-12
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Compare three powerful self-hosted search engines in 2026. Complete guide with Docker setup, configuration, and real-world use cases for Meilisearch, Typesense, and SearXNG."
---

## Meilisearch vs Typesense vs SearXNG: Best Self-Hosted Search Engines 2026

Search is the backbone of every application that deals with data. Whether you are building a documentation site, running an e-commerce platform, or creating a meta-search aggregator for your home lab, choosing the right search engine matters. Cloud-hosted solutions like Algolia, Elasticsearch Service, and Google Programmable Search lock your data behind vendor walls and growing monthly bills. Self-hosting gives you full control, zero query costs, and complete privacy.

In 2026, three open-source search engines stand out for self-hosting: **Meilisearch**, **Typesense**, and **SearXNG**. Each serves a fundamentally different purpose, and understanding their strengths helps you pick the right tool for your stack.

## Why Self-Host Your Search Engine?

Running your own search infrastructure eliminates the most frustrating aspects of cloud search providers:

- **Zero per-query costs.** Cloud search engines charge by the number of searches or indexed records. Self-hosted engines cost only your server resources.
- **Full data ownership.** Your search index never leaves your infrastructure. No analytics tracking, no data sharing with third parties, no surprise policy changes.
- **No rate limits or throttling.** Your API handles as many queries as your hardware can support. No burst penalties, no fair-usage surprises.
- **Offline capability.** Self-hosted search works entirely within your network. Ideal for air-gapped environments, intranets, and edge deployments.
- **Customization without gatekeepers.** Tune ranking algorithms, add custom filters, modify tokenizers, and extend functionality without filing support tickets.
- **Predictable scaling.** Add RAM, CPU, or disk to your server instead of negotiating enterprise pricing tiers.

The trade-off is operational responsibility — you manage backups, updates, and monitoring. With Docker, this overhead is minimal for most use cases.

## Meilisearch: The Developer-Friendly Full-Text Search Engine

Meilisearch is a Rust-based full-text search engine designed for developer experience. Its defining feature is a blazing-fast typo-tolerant search that works out of the box with zero configuration. You feed it JSON documents and get sub-50-millisecond search results with fuzzy matching, filtering, sorting, and faceted search.

### Key Features

- **Typo tolerance** — Finds results even with misspellings, transposed letters, or missing characters
- **Language-aware tokenization** — Built-in support for English, French, German, Japanese, Chinese, Korean, Thai, Hebrew, Hindi, Arabic, Russian, and more
- **Faceted search and filtering** — Filter on any attribute with complex boolean logic
- **Geo search** — Search by location with radius queries
- **Synonym support** — Define synonym groups for domain-specific terminology
- **Asynchronous indexing** — Add and update documents without blocking search queries
- **REST API** — Clean, well-documented JSON API with SDKs for JavaScript, Python, PHP, Go, Ruby, Java, and Rust

### Docker Setup

```bash
# Create a persistent data directory
mkdir -p ~/meilisearch/data

# Run Meilisearch with Docker
docker run -d \
  --name meilisearch \
  -p 7700:7700 \
  -v ~/meilisearch/data:/meili_data \
  -e MEILI_MASTER_KEY="your-secret-master-key" \
  -e MEILI_ENV="production" \
  getmeili/meilisearch:latest
```

### Docker Compose

```yaml
version: "3.8"

services:
  meilisearch:
    image: getmeili/meilisearch:latest
    container_name: meilisearch
    restart: unless-stopped
    ports:
      - "7700:7700"
    volumes:
      - meili_data:/meili_data
    environment:
      - MEILI_MASTER_KEY=your-secret-master-key
      - MEILI_ENV=production

volumes:
  meili_data:
    driver: local
```

### Indexing Documents

```bash
# Create an index and add documents
curl -X POST 'http://localhost:7700/indexes/products/documents' \
  -H 'Authorization: Bearer your-secret-master-key' \
  -H 'Content-Type: application/json' \
  -d '[
    {
      "id": 1,
      "title": "Mechanical Keyboard",
      "description": "Cherry MX Blue switches with RGB backlight",
      "category": "electronics",
      "price": 89.99,
      "in_stock": true
    },
    {
      "id": 2,
      "title": "USB-C Hub",
      "description": "7-in-1 adapter with HDMI and ethernet",
      "category": "electronics",
      "price": 34.99,
      "in_stock": true
    }
  ]'
```

### Searching

```bash
# Basic search with typo tolerance
curl 'http://localhost:7700/indexes/products/search?q=mecanical' \
  -H 'Authorization: Bearer your-secret-master-key'

# Search with filters
curl 'http://localhost:7700/indexes/products/search?q=keyboard&filter=price < 100 AND in_stock = true' \
  -H 'Authorization: Bearer your-secret-master-key'
```

The typo-tolerant search will still return "Mechanical Keyboard" for the query "mecanical" — this is Meilisearch's killer feature and works without any configuration.

### Custom Ranking Rules

```bash
# Set custom ranking order
curl -X PATCH 'http://localhost:7700/indexes/products/settings' \
  -H 'Authorization: Bearer your-secret-master-key' \
  -H 'Content-Type: application/json' \
  -d '{
    "rankingRules": [
      "words",
      "typo",
      "proximity",
      "attribute",
      "sort",
      "exactness",
      "price:asc"
    ],
    "sortableAttributes": ["price", "category"],
    "filterableAttributes": ["price", "category", "in_stock"]
  }'
```

### Best Use Cases

- **Documentation search** — Replace Algolia DocSearch with a self-hosted alternative
- **E-commerce product search** — Typo tolerance is critical for storefront search
- **Application search** — Add search to any app with minimal code
- **Small to medium datasets** — Excels with datasets under 10 million documents

---

## Typesense: The Typo-Tolerant Search Engine for Production

Typesense is a C++-based search engine built for production workloads where performance and reliability matter. It offers typo-tolerant search like Meilisearch but adds multi-tenancy, geosearch, and vector search in a single binary. Typesense uses an in-memory architecture with on-disk persistence, making it extremely fast for read-heavy workloads.

### Key Features

- **In-memory speed with disk persistence** — All data lives in RAM for microsecond query latency, with WAL-based persistence for durability
- **Multi-tenancy** — Isolated search collections with API key scoping, perfect for SaaS applications
- **Vector search** — Built-in semantic search alongside traditional full-text search
- **Geosearch** — Radius-based and bounding-box geo filtering with distance sorting
- **Curation and overrides** — Pin, hide, or promote specific results for given queries
- **Federated search** — Query multiple collections in a single request and merge results
- **Clustering** — Native high-availability clustering for production deployments
- **Analytics API** — Track popular searches, zero-result queries, and conversion metrics

### Docker Setup

```bash
# Create data directory
mkdir -p ~/typesense/data

# Run Typesense with Docker
docker run -d \
  --name typesense \
  -p 8108:8108 \
  -v ~/typesense/data:/data \
  typesense/typesense:latest \
  --data-dir /data \
  --api-key=your-secret-api-key \
  --enable-cors
```

### Docker Compose

```yaml
version: "3.8"

services:
  typesense:
    image: typesense/typesense:latest
    container_name: typesense
    restart: unless-stopped
    ports:
      - "8108:8108"
    volumes:
      - typesense_data:/data
    command: '--data-dir /data --api-key=your-secret-api-key --enable-cors'

volumes:
  typesense_data:
    driver: local
```

### Creating a Collection and Indexing

```bash
# Create a collection schema
curl 'http://localhost:8108/collections' \
  -X POST \
  -H "X-TYPESENSE-API-KEY: your-secret-api-key" \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "articles",
    "fields": [
      {"name": "title", "type": "string"},
      {"name": "content", "type": "string"},
      {"name": "author", "type": "string", "facet": true},
      {"name": "tags", "type": "string[]", "facet": true},
      {"name": "published_at", "type": "int64"},
      {"name": "views", "type": "int32"}
    ],
    "default_sorting_field": "views"
  }'

# Index a document
curl 'http://localhost:8108/collections/articles/documents' \
  -X POST \
  -H "X-TYPESENSE-API-KEY: your-secret-api-key" \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Getting Started with Docker Compose",
    "content": "A practical guide to container orchestration...",
    "author": "Jane Smith",
    "tags": ["docker", "devops", "tutorial"],
    "published_at": 1712880000,
    "views": 15420
  }'
```

### Searching with Facets

```bash
# Search with faceted filtering and sorting
curl 'http://localhost:8108/collections/articles/documents/search' \
  -H "X-TYPESENSE-API-KEY: your-secret-api-key" \
  -H 'Content-Type: application/json' \
  -d '{
    "q": "docker orchestraton",
    "query_by": "title,content",
    "filter_by": "tags:=docker && views:>1000",
    "sort_by": "views:desc",
    "per_page": 10,
    "highlight_full_fields": "title,content"
  }'
```

### Geosearch Example

```bash
# Create a collection with geo field
curl 'http://localhost:8108/collections' \
  -X POST \
  -H "X-TYPESENSE-API-KEY: your-secret-api-key" \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "locations",
    "fields": [
      {"name": "name", "type": "string"},
      {"name": "location", "type": "geopoint"}
    ]
  }'

# Search within a radius
curl 'http://localhost:8108/collections/locations/documents/search' \
  -H "X-TYPESENSE-API-KEY: your-secret-api-key" \
  -H 'Content-Type: application/json' \
  -d '{
    "q": "*",
    "filter_by": "location:(48.8566, 2.3522, 10 km)",
    "sort_by": "location(48.8566, 2.3522):asc"
  }'
```

### Best Use Cases

- **SaaS multi-tenant search** — API key scoping isolates customer data
- **E-commerce at scale** — Handles millions of products with sub-millisecond latency
- **Content platforms** — Federated search across articles, videos, and forums
- **Vector + text hybrid search** — Combine semantic and keyword search seamlessly

---

## SearXNG: The Privacy-First Meta-Search Engine

SearXNG takes a completely different approach. Rather than indexing your own data, it is a **meta-search engine** that queries dozens of search providers (Google, Bing, DuckDuckGo, Wikipedia, and 70+ more) and aggregates results while stripping all tracking identifiers. It is the ultimate privacy tool for web search.

### Key Features

- **70+ search engines** — General web search, images, videos, news, maps, IT, science, music, files, and more
- **Zero tracking** — No search history, no cookies, no profiling, no ads
- **Self-hosted instance** — Run your own instance for complete privacy
- **JSON API** — Integrate into applications, scripts, or dashboards
- **Tor support** — Route queries through Tor for maximum anonymity
- **Rate limit protection** — Built-in throttling to prevent upstream bans
- **Customizable engines** — Enable, disable, or add custom search backends
- **Result rewriting** — Remove tracking parameters from outbound links

### Docker Setup

```bash
# Clone the repository
git clone https://github.com/searxng/searxng-docker.git
cd searxng-docker

# Edit the configuration
nano .env
# Set SEARXNG_SECRET=$(openssl rand -hex 32)

# Start the service
docker compose up -d
```

### Docker Compose (Manual Setup)

```yaml
version: "3.8"

services:
  searxng:
    image: searxng/searxng:latest
    container_name: searxng
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./searxng-config:/etc/searxng:rw
    environment:
      - SEARXNG_BASE_URL=http://localhost:8080/
      - SEARXNG_SECRET=$(openssl rand -hex 32)
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETGID
      - SETUID
```

### Configuration

Create `searxng-config/settings.yml`:

```yaml
use_default_settings: true

general:
  instance_name: "My Private Search"
  debug: false
  privacypolicy_url: false
  donation_url: false

search:
  safe_search: 0
  autocomplete: "google"
  default_lang: "auto"
  formats:
    - html
    - json

server:
  port: 8080
  bind_address: "0.0.0.0"
  secret_key: "your-random-secret-key"
  limiter: true
  image_proxy: true

engines:
  - name: google
    engine: google
    shortcut: g
    disabled: false

  - name: duckduckgo
    engine: duckduckgo
    shortcut: ddg
    disabled: false

  - name: wikipedia
    engine: wikipedia
    shortcut: wp
    disabled: false

  - name: startpage
    engine: startpage
    shortcut: sp
    disabled: false
```

### Using the JSON API

```bash
# Search via API
curl 'http://localhost:8080/search?q=self+hosted+search+engines&format=json'

# Search specific categories
curl 'http://localhost:8080/search?q=linux+server&format=json&categories=it'

# Search for images
curl 'http://localhost:8080/search?q=open+source&format=json&categories=images'
```

### Reverse Proxy with Nginx

```nginx
server {
    listen 80;
    server_name search.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Best Use Cases

- **Private web search** — Replace Google with a tracking-free alternative
- **Research aggregator** — Query multiple sources simultaneously for thorough research
- **Developer tooling** — JSON API for building custom search dashboards
- **Tor-compatible browsing** — Anonymous search through the Tor network
- **Home lab search portal** — Give your household a privacy-respecting search engine

---

## Comparison: Meilisearch vs Typesense vs SearXNG

| Feature | Meilisearch | Typesense | SearXNG |
|---|---|---|---|
| **Primary purpose** | Full-text app search | Production search platform | Privacy meta-search |
| **Language** | Rust | C++ | Python |
| **Data source** | Your documents | Your documents | External search engines |
| **Indexing** | JSON documents | JSON documents | N/A (queries others) |
| **Typo tolerance** | Excellent | Excellent | Depends on upstream |
| **Vector search** | No | Yes | No |
| **Geo search** | Yes | Yes | No |
| **Faceted search** | Yes | Yes | Limited |
| **Multi-tenancy** | API key scoping | Full tenant isolation | Single instance |
| **Clustering / HA** | No (single node) | Yes (native) | No (single node) |
| **Memory model** | Memory-mapped files | In-memory + disk WAL | In-memory cache |
| **Max dataset** | ~10M docs (single node) | Scales with RAM | Unlimited (depends on upstream) |
| **JSON API** | Yes | Yes | Yes |
| **Web UI** | Admin dashboard | Minimal (API-first) | Full search interface |
| **Docker ready** | Yes | Yes | Yes |
| **License** | MIT | Apache 2.0 | AGPL 3.0 |
| **Best for** | Docs, small e-commerce | SaaS, large catalogs | Private web search |

---

## Choosing the Right Engine

The decision comes down to what you are searching **over**:

**Choose Meilisearch if:**
- You need search for your own data (documents, products, articles)
- Developer experience and quick setup are priorities
- Typo tolerance out of the box is critical
- Your dataset fits on a single server (under ~10 million records)
- You want the simplest possible integration path

**Choose Typesense if:**
- You are building a SaaS product with multi-tenant search
- You need high availability with native clustering
- Your workload is read-heavy and latency-sensitive
- You want vector search alongside traditional keyword search
- You need advanced features like result curation, overrides, and analytics

**Choose SearXNG if:**
- You want a private alternative to Google for web browsing
- You need to aggregate results from multiple search engines
- You are building a research tool or custom search dashboard
- Privacy and anonymity are your top priorities
- You do not need to index your own documents

---

## Production Deployment Tips

### Resource Planning

```
Meilisearch (single node):
  Minimum: 2 CPU, 4 GB RAM, 50 GB SSD
  Comfortable: 4 CPU, 8 GB RAM, 100 GB SSD

Typesense (single node):
  Minimum: 2 CPU, RAM = dataset size + 2 GB
  Comfortable: 4 CPU, RAM = 2x dataset size, 50 GB SSD

SearXNG:
  Minimum: 1 CPU, 512 MB RAM, 5 GB disk
  Comfortable: 2 CPU, 1 GB RAM, 10 GB disk
```

### Backup Strategies

```bash
# Meilisearch backup — stop the container, copy the data directory
docker stop meilisearch
cp -r ~/meilisearch/data ~/meilisearch/backup-$(date +%Y%m%d)
docker start meilisearch

# Typesense snapshot — use the snapshot endpoint
curl -X POST 'http://localhost:8108/operations/snapshot' \
  -H "X-TYPESENSE-API-KEY: your-secret-api-key" \
  -H 'Content-Type: application/json' \
  -d '{"snapshot_path": "/data/snapshots/backup-20260412"}'

# SearXNG backup — only settings need backup
tar czf searxng-backup.tar.gz ./searxng-config
```

### Monitoring

```yaml
# Add health checks to your docker-compose
  meilisearch:
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:7700/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  typesense:
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:8108/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  searxng:
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:8080/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## Final Verdict

All three engines excel at their intended purpose. Meilisearch wins on simplicity and developer experience — it is the fastest path from zero to working search. Typesense wins on features and scale — it is a production-grade platform with clustering, vector search, and multi-tenancy. SearXNG wins on privacy — it is the only option that gives you a tracking-free web search experience.

For most self-hosted application search needs, start with Meilisearch. If you outgrow it or need high availability, migrate to Typesense. For private web browsing, deploy SearXNG alongside either of the other two — they complement each other perfectly.
