---
title: "OpenReplay vs Highlight vs PostHog: Best Self-Hosted Session Replay 2026"
date: 2026-04-15
tags: ["comparison", "guide", "self-hosted", "privacy", "analytics", "developer-tools"]
draft: false
description: "Complete guide to self-hosted session replay in 2026. Compare OpenReplay, Highlight.io, and PostHog — open-source alternatives to FullStory, Hotjar, and LogRocket with Docker setup and configuration."
---

Session replay has become one of the most valuable debugging and product intelligence tools available to engineering teams. Instead of guessing why a user encountered an error or abandoned a checkout flow, you can watch exactly what they saw, where they clicked, and which requests failed — frame by frame. Commercial platforms like FullStory, Hotjar, LogRocket, and Smartlook dominate this space, but they come with significant trade-offs: every recorded session leaves your infrastructure, pricing scales steeply with traffic, and retention windows are tightly controlled by the vendor.

In 2026, self-hosted session replay has matured into a practical alternative. Three open-source platforms stand out: **OpenReplay**, **Highlight.io**, and **PostHog** (with its session replay module). Each can replace commercial session replay products while keeping user data on your own servers, under your control, and without per-session pricing surprises.

This guide compares all three, with step-by-step [docker](https://www.docker.com/) deployment instructions, configuration details, and a head-to-head feature breakdown to help you choose the right platform for your team.

## Why Self-Host Your Session Replay

Running session replay on your own infrastructure delivers advantages that hosted platforms cannot match:

**Complete data privacy.** Session recordings capture everything a user does on your application — every click, scroll, form input, and navigation event. When you send this data to a third-party service, you are entrusting them with potentially sensitive information including personal details, payment form interactions, and internal tool usage. Self-hosting ensures session data never leaves your security boundary, simplifying GDPR, HIPAA, SOC 2, and internal compliance requirements.

**Unlimited recording volume.** Commercial session replay platforms price by the number of recorded sessions or by data ingestion volume. A busy SaaS application processing thousands of sessions per day can easily face $500–$5,000+ per month in session replay costs. Self-hosted solutions run on your existing infrastructure with no per-session fees, no sampling caps, and no surprise overage charges.

**Full retention control.** Hosted platforms typically retain session data for 30–90 days on standard plans, with extended retention locked behind enterprise pricing. When you self-host, you decide how long to keep recordings. Need to replay a session from six months ago for a support investigation or compliance audit? The data is there.

**Deeper integration potential.** Running the software yourself means you can connect session replay data directly to your internal systems — your error tracker, your logging pipeline, your customer support platform, and your data warehouse. You can also modify the platform itself to capture custom events, extend the player interface, or integrate with proprietary authentication systems.

**No vendor lock-in.** Your session recordings, metadata, and analytics data belong to you. There is no proprietary export format or API dependency holding your historical data hostage if you ever decide to switch tools.

## What Is Session Replay?

Session replay works by recording the DOM mutations, user interactions, and network activity that occur during a user's visit to your application. A lightweight JavaScript SDK running in the browser captures:

- **DOM snapshots** — periodic recordings of the page structure and content
- **DOM mutations** — real-time tracking of changes to the page (text updates, element additions/removals, style changes)
- **User interactions** — mouse movements, clicks, taps, scrolls, keyboard input, and touch gestures
- **Network activity** — HTTP requests and responses, including headers, status codes, and response bodies
- **Console output** — browser console logs, warnings, and errors
- **Performance metrics** — page load times, resource timing, and long task detection

The SDK compresses this data and streams it to your backend, where it is stored and indexed. The replay player reconstructs the session by replaying the recorded DOM mutations and events in sequence, creating a video-like experience that lets you see exactly what the user experienced.

Unlike actual screen recording, session replay does not capture video frames. Instead, it records a log of changes that the player re-applies to recreate the session. This approach produces significantly smaller files (typically 100–500 KB per minute of recording versus several megabytes for video) and allows the player to overlay additional information like network timelines and error markers.

## OpenReplay: Full-Featured Session Replay Platform

**OpenReplay** is the most comprehensive open-source session replay platform available today. It was purpose-built as a self-hosted alternative to FullStory and LogRocket, offering session replay alongside error tracking, product analytics, and developer tools in a single platform. OpenReplay supports web applications, mobile apps (iOS and Android), and backend services.

### Key Features

- **Full session replay** with DOM recording, mouse tracking, and network inspection
- **Error tracking** with automatic detection of JavaScript errors and unhandled promise rejections
- **Product analytics** including funnels, retention curves, and custom event tracking
- **Assist** — real-time co-browsing for live support sessions
- **DevTools replay** — integrates with your backend logs, APM data, and infrastructure metrics
- **Mobile session replay** for iOS and Android applications via native SDKs
- **Advanced filtering** — search sessions by URL, browser, device, country, referrer, duration, and custom metadata
- **Session scoring** — automatically identify rage clicks, dead clicks, and error-heavy sessions
- **Slack and webhook integrations** for alerting on critical session patterns
- **PostgreSQL and ClickHouse** storage backends

### Architecture

OpenReplay runs as a collection of microservices depl[kubernetes](https://kubernetes.io/)ocker Compose or Kubernetes:

1. **Chasqu (frontend)** — the web UI for replay viewing, search, and analytics
2. **Backend API** — handles session ingestion, storage, and query processing
3. **ClickHouse** — columnar database for fast session search and analytics queries
4. **PostgreSQL** — relational database for user accounts, project configuration, and metadata
5. **Redis** — caching layer and message queue for session processing
6. **S3-compatible storage** — stores compressed session recording data (MinIO, AWS S3, or any S3-compatible backend)

### Docker Compose Installation

OpenReplay provides an official deployment script that sets up the complete stack:

```bash
# Clone the OpenReplay repository
git clone https://github.com/openreplay/openreplay.git
cd openreplay

# Run the deployment script
sudo ./deploy.sh

# The script will:
# - Pull all required Docker images
# - Set up ClickHouse, PostgreSQL, and Redis
# - Deploy the backend API and frontend
# - Configure MinIO for session storage
# - Start all services
```

Alternatively, you can deploy with Docker Compose directly:

```yaml
version: "3.8"

services:
  openreplay-clickhouse:
    image: clickhouse/clickhouse-server:latest
    container_name: openreplay-clickhouse
    ports:
      - "8123:8123"
      - "9000:9000"
    volumes:
      - clickhouse_data:/var/lib/clickhouse
    environment:
      CLICKHOUSE_DB: openreplay
      CLICKHOUSE_USER: openreplay
      CLICKHOUSE_PASSWORD: ${CLICKHOUSE_PASSWORD}

  openreplay-postgres:
    image: postgres:16-alpine
    container_name: openreplay-postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: openreplay
      POSTGRES_USER: openreplay
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}

  openreplay-redis:
    image: redis:7-alpine
    container_name: openreplay-redis
    ports:
      - "6379:6379"

  openreplay-minio:
    image: minio/minio:latest
    container_name: openreplay-minio
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data
    environment:
      MINIO_ROOT_USER: ${MINIO_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}
    command: server /data --console-address ":9001"

volumes:
  clickhouse_data:
  postgres_data:
  minio_data:
```

After deployment, the OpenReplay UI is available at `http://localhost:8080`. Create a project and grab the tracking snippet from the project settings.

### SDK Integration

Add the OpenReplay tracker to your web application:

```bash
npm install @openreplay/tracker
```

```javascript
import Tracker from '@openreplay/tracker';

const tracker = new Tracker({
  projectKey: 'YOUR_PROJECT_KEY',
  ingestPoint: 'https://your-openreplay-domain.com/ingest',
  defaultInputMode: 0,
  sessionReset: true,
});

tracker.start();

// Tag sessions with user identity
tracker.setUserID('user-12345');
tracker.setMetadata('email', 'user@example.com');
tracker.setMetadata('plan', 'premium');

// Track custom events
tracker.event('checkout-started', { cartTotal: 149.99 });
```

### Resource Requirements

For a moderate workload (10,000 sessions/day), plan for:

- **CPU:** 4 cores minimum
- **RAM:** 8 GB minimum (16 GB recommended)
- **Storage:** 100 GB SSD for ClickHouse and session data
- **Network:** Stable internet connection for SDK ingestion

## Highlight.io: Session Replay + Error Monitoring Combined

**Highlight.io** combines session replay with error monitoring, logging, and tracing in a unified platform. It positions itself as an open-source alternative to the combination of Sentry + LogRocket + Datadog RUM. Highlight.io is particularly strong at connecting session replays directly to the errors that occurred during those sessions, making it a favorite among engineering teams focused on debugging.

### Key Features

- **Session replay** with full DOM recording and interaction tracking
- **Error monitoring** with automatic JavaScript error capture and source map support
- **Frontend logging** — structured log collection from the browser
- **Backend tracing** — OpenTelemetry-compatible distributed tracing
- **Session-to-error linking** — click from an error directly to the exact moment it occurred in the replay
- **Custom metrics** — track application-specific KPIs alongside session data
- **Team collaboration** — share sessions with annotations and comments
- **Privacy controls** — field masking, input redaction, and URL filtering
- **Docker-based self-hosted deployment**

### Architecture

Highlight.io's self-hosted deployment consists of:

1. **Frontend** — React-based web UI for session viewing and error exploration
2. **Backend API** — Go-based service handling ingestion, storage, and queries
3. **PostgreSQL** — metadata storage for sessions, errors, and project configuration
4. **ClickHouse** — high-performance analytics and session data storage
5. **Object storage** — S3-compatible backend for replay data (MinIO or cloud S3)

### Docker Compose Installation

Highlight.io provides Helm charts for Kubernetes and a Docker Compose setup for simpler deployments:

```bash
# Clone the Highlight repository
git clone https://github.com/highlight/highlight.git
cd highlight

# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
# Set secure passwords for all services
```

```yaml
version: "3.8"

services:
  highlight-postgres:
    image: postgres:16-alpine
    container_name: highlight-postgres
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: highlight
      POSTGRES_USER: highlight
      POSTGRES_PASSWORD: ${HIGHLIGHT_PG_PASSWORD}

  highlight-clickhouse:
    image: clickhouse/clickhouse-server:latest
    container_name: highlight-clickhouse
    ports:
      - "8123:8123"
    volumes:
      - ch_data:/var/lib/clickhouse
    environment:
      CLICKHOUSE_DB: highlight
      CLICKHOUSE_USER: highlight
      CLICKHOUSE_PASSWORD: ${HIGHLIGHT_CH_PASSWORD}

  highlight-backend:
    image: highlight/highlight-backend:latest
    container_name: highlight-backend
    ports:
      - "8080:8080"
    depends_on:
      - highlight-postgres
      - highlight-clickhouse
    environment:
      DATABASE_URI: postgres://highlight:${HIGHLIGHT_PG_PASSWORD}@highlight-postgres:5432/highlight
      CLICKHOUSE_DSN: clickhouse://highlight:${HIGHLIGHT_CH_PASSWORD}@highlight-clickhouse:8123/highlight
      S3_ENDPOINT: http://highlight-minio:9000
      S3_BUCKET: highlight-sessions
      S3_ACCESS_KEY_ID: ${MINIO_USER}
      S3_SECRET_ACCESS_KEY: ${MINIO_PASSWORD}

  highlight-frontend:
    image: highlight/highlight-frontend:latest
    container_name: highlight-frontend
    ports:
      - "3000:3000"
    depends_on:
      - highlight-backend

  highlight-minio:
    image: minio/minio:latest
    container_name: highlight-minio
    ports:
      - "9000:9000"
    volumes:
      - minio_data:/data
    environment:
      MINIO_ROOT_USER: ${MINIO_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}
    command: server /data

volumes:
  pg_data:
  ch_data:
  minio_data:
```

### SDK Integration

Install and configure the Highlight SDK:

```bash
npm install highlight.run
```

```javascript
import { H } from 'highlight.run';

H.init('YOUR_PROJECT_ID', {
  backendUrl: 'https://your-highlight-domain.com',
  tracingOrigins: true,
  networkRecording: {
    enabled: true,
    recordHeadersAndBody: true,
    urlBlocklist: ['/health', '/metrics'],
  },
  privacySetting: 'strict', // or 'standard'
});

// Associate session with a user
H.identify('user-12345', {
  email: 'user@example.com',
  name: 'Jane Doe',
});

// Track custom events
H.track('purchase-completed', {
  amount: 49.99,
  currency: 'USD',
  items: 3,
});
```

### Privacy and Redaction

Highlight.io provides granular privacy controls:

```javascript
// Mask all input fields by default
H.init('YOUR_PROJECT_ID', {
  privacySetting: 'strict',
});

// Allow specific fields through
H.identify('user-12345', {
  email: 'user@example.com',
}, {
  maskInputs: false, // allow input recording for authenticated users
});

// URL-based filtering
H.init('YOUR_PROJECT_ID', {
  excludedHostnamePatterns: ['localhost', 'staging.example.com'],
  sessionSampleRate: 0.5, // record 50% of sessions
});
```

## PostHog Session Replay: Analytics-Native Replay

**PostHog** is best known as a self-hosted product analytics platform, but its session replay module has grown into a fully featured recording system. The key advantage of PostHog session replay is its native integration with product analytics — every replay is automatically linked to the events, funnels, and user properties you are already tracking.

### Key Features

- **Session replay** with DOM recording and interaction playback
- **Native event integration** — every replay is linked to your PostHog events automatically
- **Funnel analysis with replay** — watch replays of users who dropped off at specific funnel steps
- **Feature flag correlation** — see how different feature flag variants affect user behavior
- **A/B test replay** — compare session replays across experiment variants
- **Person profiles** — link replays to individual user profiles with all their historical data
- **Error tracking** — built-in JavaScript error capture linked to replays
- **Heatmaps** — aggregate click and scroll data across all sessions
- **Surveys** — collect user feedback triggered by session behavior
- **PostHog Cloud or self-hosted** deployment options

### Architecture

PostHog's self-hosted deployment is more com[plex](https://www.plex.tv/) than the other two options, reflecting its broader feature set:

1. **Web app** — Django-based frontend and API
2. **Event pipeline** — Kafka-based event ingestion and processing
3. **ClickHouse** — analytics and session data storage
4. **PostgreSQL** — user accounts, project configuration, and person profiles
5. **Redis** — caching and task queue
6. **Object storage** — S3-compatible backend for replay recordings

### Docker Compose Installation

PostHog provides a comprehensive Docker Compose setup:

```bash
# Clone the PostHog repository
git clone https://github.com/PostHog/posthog.git
cd posthog

# Copy and configure the environment
cp .env.example .env

# Start the full stack
docker compose up -d
```

```yaml
# Simplified excerpt — the full PostHog compose file includes
# ClickHouse, Kafka, Zookeeper, PostgreSQL, Redis, and the web app
version: "3.8"

services:
  web:
    image: posthog/posthog:latest
    container_name: posthog-web
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
      - clickhouse
      - kafka
    environment:
      DATABASE_URL: postgres://posthog:${PG_PASSWORD}@postgres:5432/posthog
      CLICKHOUSE_HOST: clickhouse
      KAFKA_HOSTS: kafka:9092
      REDIS_URL: redis://redis:6379
      SECRET_KEY: ${POSTHOG_SECRET_KEY}

  postgres:
    image: postgres:16-alpine
    container_name: posthog-postgres
    volumes:
      - pg_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: posthog
      POSTGRES_USER: posthog
      POSTGRES_PASSWORD: ${PG_PASSWORD}

  clickhouse:
    image: clickhouse/clickhouse-server:latest
    container_name: posthog-clickhouse
    volumes:
      - ch_data:/var/lib/clickhouse

  kafka:
    image: apache/kafka:latest
    container_name: posthog-kafka

  redis:
    image: redis:7-alpine
    container_name: posthog-redis

volumes:
  pg_data:
  ch_data:
```

The PostHog UI is available at `http://localhost:8000` after startup. Initial setup walks you through project creation and SDK configuration.

### SDK Integration

The PostHog SDK enables both analytics and session replay:

```bash
npm install posthog-js
```

```javascript
import posthog from 'posthog-js';

posthog.init('YOUR_PROJECT_API_KEY', {
  api_host: 'https://your-posthog-domain.com',
  capture_pageview: true,
  session_recording: {
    enabled: true,
    maskAllInputs: true,
    maskInputOptions: { password: true },
    // Record a percentage of sessions to manage storage
    sampleRate: '0.5',
    // Minimum duration before recording starts
    minimumDuration: 5000,
  },
  person_profiles: 'identified_only',
});

// Identify users
posthog.identify('user-12345', {
  email: 'user@example.com',
  plan: 'premium',
});

// Track events (automatically linked to session replay)
posthog.capture('checkout_started', {
  cartValue: 149.99,
  itemCount: 3,
});
```

## Head-to-Head Comparison

| Feature | OpenReplay | Highlight.io | PostHog |
|---------|-----------|-------------|---------|
| **Session replay** | Full DOM + mobile | Full DOM | Full DOM |
| **Error tracking** | Built-in | Built-in | Built-in |
| **Product analytics** | Basic funnels | Limited | Full suite |
| **Mobile replay** | iOS + Android SDKs | React Native | Limited |
| **Assist/co-browsing** | Yes | No | No |
| **A/B test integration** | No | No | Native |
| **Heatmaps** | No | No | Built-in |
| **Feature flags** | No | No | Built-in |
| **Network recording** | Yes | Yes | Yes |
| **Console recording** | Yes | Yes | Yes |
| **Privacy controls** | Input masking | Field-level redaction | Input masking |
| **Storage backend** | ClickHouse + S3 | ClickHouse + S3 | ClickHouse + S3 |
| **Docker deployment** | Official script | Docker Compose | Docker Compose |
| **Kubernetes support** | Helm chart | Helm chart | Helm chart |
| **Min. resources** | 4 CPU / 8 GB RAM | 2 CPU / 4 GB RAM | 4 CPU / 8 GB RAM |
| **Complexity** | Medium | Low | High |
| **Best for** | Support teams + devs | Engineering/debugging | Product teams |

## Which One Should You Choose?

**Choose OpenReplay if** your primary need is session replay with strong support team features. OpenReplay's Assist co-browsing, mobile SDK support, and session scoring (rage clicks, dead clicks) make it ideal for customer support teams and QA engineers who need to investigate user issues at scale. The DevTools integration with backend logs and APM data is also a strong differentiator for engineering teams debugging complex multi-tier issues.

**Choose Highlight.io if** you want the simplest deployment with the tightest error-to-session integration. Highlight.io's architecture is the lightest of the three, and its strength lies in connecting every error directly to the session replay where it occurred. If your team's primary workflow is "something broke, let me see what the user experienced," Highlight.io is the most direct path from error alert to session replay.

**Choose PostHog if** session replay is one piece of a broader product analytics strategy. PostHog's session replay is fully integrated with event tracking, funnels, feature flags, A/B testing, and person profiles. If you are already using or planning to use PostHog for product analytics, enabling session replay is a natural extension that gives you replay-linked funnel analysis and experiment variant comparison out of the box.

## Performance and Storage Considerations

Session replay generates significant data. Plan your infrastructure accordingly:

- **Storage per session:** A 5-minute session typically produces 1–3 MB of compressed recording data
- **Daily volume:** 10,000 sessions/day at an average of 2 MB each = ~20 GB/day
- **Retention:** 30 days of retention at 20 GB/day = ~600 GB of storage
- **ClickHouse storage:** Analytics indexes add approximately 20–30% on top of raw recording data

To manage costs, implement a tiered retention strategy:

```bash
# Example: Keep recent sessions on fast SSD, archive older ones to cold storage
# OpenReplay supports S3 lifecycle policies for automatic tiering

# Configure MinIO lifecycle policy
mc ilm add --expiry-days 30 mybucket/sessions
mc ilm add --transition-days 7 --storage-class GLACIER mybucket/sessions
```

Consider recording sampling for high-traffic applications:

```javascript
// Record 100% of sessions with errors, 20% of all others
posthog.init('YOUR_KEY', {
  session_recording: {
    sampleRate: '0.2',
    // Always record sessions where an error occurs
    recordOn: (session) => session.hasError ? '1.0' : '0.2',
  },
});
```

## Conclusion

Self-hosted session replay in 2026 is a practical, production-ready alternative to commercial platforms. OpenReplay leads in feature breadth and support team capabilities, Highlight.io offers the cleanest error-to-replay workflow with minimal deployment overhead, and PostHog delivers the deepest integration with product analytics. All three keep your session data on your own infrastructure, eliminate per-session pricing, and give you full control over retention and privacy policies.

Pick the platform that matches your team's primary workflow, deploy it with Docker, and start understanding exactly what your users experience — without sending a byte of session data to a third party.

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
