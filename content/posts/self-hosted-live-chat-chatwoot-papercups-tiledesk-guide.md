---
title: "Best Self-Hosted Live Chat Solutions 2026: Chatwoot vs Papercups vs Tiledesk"
date: 2026-04-14
tags: ["comparison", "guide", "self-hosted", "customer-support"]
draft: false
description: "Compare the best self-hosted live chat platforms in 2026. Full Docker deployment guides for Chatwoot, Papercups, and Tiledesk as open-source alternatives to Intercom and Zendesk."
---

## Why Self-Host Your Live Chat?

Every website needs a way for visitors to reach you in real time. The SaaS live chat market is dominated by Intercom, Zendesk Chat, Drift, and Freshdesk — polished products that come with significant trade-offs:

**Cost at scale.** Intercom starts at $74/month for a single seat and scales to hundreds of dollars as your team and conversation volume grow. For bootstrapped startups, small businesses, and open-source projects, this pricing is a serious barrier.

**Data privacy and ownership.** When you use a cloud live chat widget, every conversation, every visitor IP address, every behavioral event flows through a third party's servers. If you serve customers in the EU, handle regulated industries, or simply value privacy, this is a fundamental problem. You cannot guarantee data sovereignty when the vendor decides where to store your data.

**Vendor lock-in.** Your entire conversation history, customer profiles, and automated workflows live in the vendor's database. Migrating away is painful and usually means starting from scratch.

**Feature gating.** SaaS vendors dangle essential features — custom branding, API access, advanced routing, SLA management — behind expensive tiers. Self-hosted solutions give you the full feature set from day one.

Self-hosting a live chat platform solves all of these problems. You own the data, you control the infrastructure, and you pay zero per-seat licensing fees. The trade-off is operational responsibility — but with Docker, it has never been easier.

Three open-source projects lead the self-hosted live chat space in 2026: **Chatwoot**, **Papercups**, and **Tiledesk**. Each takes a fundamentally different approach, targets different use cases, and offers distinct architectural trade-offs. This guide compares all three across features, deployment complexity, and usability — and provides production-ready Docker configurations so you can deploy the one that fits your needs.

---

## The Contenders at a Glance

| Feature | Chatwoot | Papercups | Tiledesk |
|---------|----------|-----------|----------|
| **Language / Stack** | Ruby on Rails + Vue.js + PostgreSQL + Redis | Elixir (Phoenix) + PostgreSQL + React | Node.js + MongoDB |
| **License** | MIT | Apache 2.0 | AGPLv3 |
| **GitHub Stars** | 20,000+ | 3,500+ | 2,500+ |
| **Live Chat Widget** | ✅ Customizable | ✅ Lightweight | ✅ Full-featured |
| **Email Channel** | ✅ Yes | ❌ No | ✅ Yes |
| **Social Channels** | Twitter, Facebook, Telegram, WhatsApp, SMS, Line | ❌ No | WhatsApp, Facebook, Telegram |
| **Team Inbox** | ✅ Multi-agent | ✅ Multi-agent | ✅ Multi-agent |
| **Canned Responses** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Chatbots / Automation** | ✅ Workflow automation | ⚠️ Basic | ✅ AI bots + rules |
| **Knowledge Base** | ✅ Built-in | ❌ No | ✅ Built-in |
| **Mobile Apps** | iOS + Android | ❌ No | iOS + Android |
| **Real-time Typing** | ✅ Yes | ✅ Yes | ✅ Yes |
| **File Sharing** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Analytics Dashboard** | ✅ Yes | ⚠️ Basic | ✅ Yes |
| **Multi-Brand** | ✅ Yes | ❌ No | ✅ Yes |
| **Docker Compose** | ✅ Official | ✅ Community | ✅ Official |
| **API** | REST + Webhooks | REST + WebSocket | REST + Webhooks |
| **Resource Requirements** | Medium (Rails) | Low (Elixir) | Medium (Node.js) |
| **Ideal For** | Full customer engagement platform | Simple, fast live chat widget | Omnichannel with AI bots |

---

## Chatwoot: The Full-Stack Customer Engagement Platform

Chatwoot is the most mature and feature-complete open-source live chat solution available today. Originally created as an open-source Intercom alternative, it has evolved into a comprehensive customer engagement platform that supports live chat, email, social media, and even WhatsApp — all through a unified inbox.

### Key Advantages

- **Multi-channel support**: Aggregates conversations from website chat, email, Twitter/X, Facebook, Telegram, WhatsApp, SMS, and Line into a single inbox. Agents never need to switch between platforms.
- **Team collaboration**: Assign conversations, add private notes, mention teammates, and set conversation status (open, pending, resolved).
- **Built-in knowledge base**: Create help articles and link them to your chat widget so visitors can self-serve before starting a conversation.
- **Workflow automation**: Set up rules that auto-assign conversations, send canned responses, escalate to specific agents, or trigger webhooks based on conversation metadata.
- **Custom branding**: White-label the chat widget with your colors, logo, and custom domain. No Chatwoot branding required.
- **Mobile apps**: Native iOS and Android apps mean your team can respond to conversations on the go.
- **Active ecosystem**: Over 20,000 GitHub stars, regular releases, and a growing marketplace of integrations.

### Architecture

Chatwoot runs on Ruby on Rails for the backend API, Vue.js for the web dashboard, PostgreSQL for persistent data, and Redis for real-time Pub/Sub and job queues. The architecture is battle-tested and can handle thousands of concurrent conversations when properly scaled.

### Production Docker Compose Setup

Here's a complete, production-ready deployment with PostgreSQL, Redis, and a Caddy reverse proxy for automatic HTTPS:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: chatwoot-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: chatwoot
      POSTGRES_USER: chatwoot
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-chatwoot_secret_pass}
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U chatwoot"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: chatwoot-redis
    restart: unless-stopped
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  chatwoot:
    image: chatwoot/chatwoot:latest
    container_name: chatwoot
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - POSTGRES_HOST=postgres
      - POSTGRES_PORT=5432
      - POSTGRES_DATABASE=chatwoot
      - POSTGRES_USERNAME=chatwoot
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-chatwoot_secret_pass}
      - REDIS_URL=redis://redis:6379
      - FRONTEND_URL=https://chat.example.com
      - SECRET_KEY_BASE=${SECRET_KEY_BASE}
      - RAILS_ENV=production
      - NODE_ENV=production
      - INSTALLATION_ENV=docker
      - MAILER_SENDER_EMAIL=support@example.com
      - SMTP_ADDRESS=smtp.example.com
      - SMTP_PORT=587
      - SMTP_USERNAME=smtp_user
      - SMTP_PASSWORD=${SMTP_PASSWORD}
      - SMTP_AUTHENTICATION=plain
      - ENABLE_ACCOUNT_SIGNUP=false
    volumes:
      - storage:/app/storage
    ports:
      - "3000:3000"

  caddy:
    image: caddy:2-alpine
    container_name: chatwoot-caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - chatwoot

volumes:
  pg_data:
  redis_data:
  storage:
  caddy_data:
  caddy_config:
```

**Caddyfile** for automatic HTTPS:

```
chat.example.com {
    reverse_proxy chatwoot:3000
    encode gzip
}
```

### Initial Setup

After the containers start, run the database migrations and create your admin account:

```bash
# Initialize the database
docker exec -it chatwoot bundle exec rails db:chatwoot_prepare

# Generate a secret key if you haven't already
docker exec -it chatwoot bundle exec rake secret

# Create a super admin user
docker exec -it chatwoot bundle exec rails chatwoot:superadmin:create
```

Set `SECRET_KEY_BASE` in your `.env` file using the output from the `rake secret` command. Then navigate to `https://chat.example.com` and log in with the credentials you just created.

### Embedding the Widget

Once you've created an inbox in the Chatwoot dashboard, you'll get a JavaScript snippet to embed on your website:

```html
<script>
  (function(d,t) {
    var BASE_URL="https://chat.example.com";
    var g=d.createElement(t),s=d.getElementsByTagName(t)[0];
    g.src=BASE_URL+"/packs/js/sdk.js";
    g.defer = true;
    g.async = true;
    s.parentNode.insertBefore(g,s);
    g.onload=function(){
      window.chatwootSDK.run({
        websiteToken: "YOUR_WEBSITE_TOKEN",
        baseUrl: BASE_URL
      })
    }
  })(document,"script");
</script>
```

---

## Papercups: The Minimalist, High-Performance Chat

Papercups takes a fundamentally different approach. Built with Elixir and the Phoenix framework, it prioritizes raw performance and simplicity over feature breadth. If Chatwoot is the Swiss Army knife, Papercups is a scalpel — one thing done exceptionally well.

### Key Advantages

- **Blazing fast**: Elixir's actor model and Phoenix Channels handle tens of thousands of concurrent WebSocket connections on a single server with minimal resource usage. The entire stack runs comfortably on 256 MB of RAM.
- **Simple deployment**: Fewer moving parts than Chatwoot. Just a web process, a PostgreSQL database, and that's it — no Redis dependency, no background job queues to manage.
- **Lightweight widget**: The chat widget is under 10 KB gzipped. It loads instantly even on slow mobile connections and doesn't slow down your page.
- **Slack integration**: Routes incoming chat messages directly to Slack channels, so your team can respond without leaving their primary communication tool.
- **Real-time typing indicators**: Visitors see when an agent is typing, and agents see when the visitor is typing — a small UX detail that significantly improves engagement.

### Architecture

Papercups uses Elixir's Phoenix framework for the web layer and real-time WebSocket communication via Phoenix Channels. PostgreSQL handles data persistence. There is no Redis, no background workers, no message broker — the entire application is a single Phoenix process.

### Docker Compose Setup

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: papercups-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: papercups_prod
      POSTGRES_USER: papercups
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-papercups_secret}
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U papercups"]
      interval: 10s
      timeout: 5s
      retries: 5

  papercups:
    image: papercups/papercups:latest
    container_name: papercups
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "4000:4000"
    environment:
      - DATABASE_URL=ecto://papercups:${POSTGRES_PASSWORD:-papercups_secret}@postgres/papercups_prod
      - SECRET_KEY_BASE=${SECRET_KEY_BASE}
      - URL=https://chat.example.com
      - MAILER_ADAPTER=bamboo
      - SMTP_HOST_ADDR=smtp.example.com
      - SMTP_HOST_PORT=587
      - SMTP_USER_EMAIL=smtp_user
      - SMTP_USER_PWD=${SMTP_PASSWORD}
      - DEFAULT_SUPPORT_EMAIL=support@example.com

volumes:
  pg_data:
```

### Nginx Reverse Proxy

Since Papercups uses WebSockets extensively, your reverse proxy must be configured for WebSocket upgrades:

```nginx
server {
    listen 443 ssl http2;
    server_name chat.example.com;

    ssl_certificate /etc/letsencrypt/live/chat.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/chat.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:4000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
}
```

### Embedding the Widget

```html
<script>
  window.PAPERCUPS_BASE_URL = "https://chat.example.com";
</script>
<script src="https://chat.example.com/embed.js" async></script>
```

---

## Tiledesk: The Omnichannel Platform with AI Bots

Tiledesk approaches live chat from a different angle: it is an omnichannel customer engagement platform built around chatbot automation. While Chatwoot focuses on human agents and Papercups focuses on simplicity, Tiledesk focuses on automating the first line of support with AI-powered bots before escalating to human agents.

### Key Advantages

- **AI-powered chatbots**: Build conversational bots using a visual designer. Bots can answer FAQs, collect user information, create support tickets, and escalate to human agents — all without human intervention.
- **Omnichannel**: Supports website chat, WhatsApp, Facebook Messenger, Telegram, and email through a unified interface.
- **Pre-chat forms**: Collect visitor name, email, and custom fields before starting the conversation — useful for lead qualification and support routing.
- **Department-based routing**: Automatically route conversations to the right team based on the visitor's question, language, or pre-chat form answers.
- **Canned responses and quick replies**: Speed up agent response times with predefined answers.
- **Triggers and webhooks**: Automate actions based on conversation events — send notifications, update external systems, or trigger workflows.
- **Multi-project support**: Manage multiple brands or websites from a single Tiledesk installation.

### Architecture

Tiledesk is built on Node.js with MongoDB as the primary database. It uses WebSocket connections for real-time communication and supports horizontal scaling through its microservice architecture. The platform includes separate services for the API, the webhook engine, and the chatbot engine.

### Docker Compose Setup

```yaml
version: '3.8'

services:
  mongo:
    image: mongo:7
    container_name: tiledesk-mongo
    restart: unless-stopped
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGO_USER:-tiledesk}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD:-tiledesk_secret}
    volumes:
      - mongo_data:/data/db
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5

  tiledesk-server:
    image: tiledesk/tiledesk-server:latest
    container_name: tiledesk-server
    restart: unless-stopped
    depends_on:
      mongo:
        condition: service_healthy
    environment:
      - MONGODB_URI=mongodb://${MONGO_USER:-tiledesk}:${MONGO_PASSWORD:-tiledesk_secret}@mongo:27017/tiledesk?authSource=admin
      - SUPER_PASSWORD=${SUPER_PASSWORD:-super_secret_admin}
      - EMAIL_BASEURL=https://chat.example.com
      - EMAIL_SENDER=support@example.com
    ports:
      - "3000:3000"

  tiledesk-dashboard:
    image: tiledesk/tiledesk-dashboard:latest
    container_name: tiledesk-dashboard
    restart: unless-stopped
    depends_on:
      - tiledesk-server
    ports:
      - "8081:80"
    environment:
      - API_BASEURL=https://chat.example.com/api
      - BRAND_NAME="My Company"

  caddy:
    image: caddy:2-alpine
    container_name: tiledesk-caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - tiledesk-server
      - tiledesk-dashboard

volumes:
  mongo_data:
  caddy_data:
  caddy_config:
```

### Embedding the Widget

```html
<script src="https://chat.example.com/widget.js"></script>
<script>
  window.tiledeskSettings = {
    projectid: "YOUR_PROJECT_ID"
  };
  (function (w, d) {
    var s = d.createElement('script');
    s.type = 'text/javascript';
    s.async = true;
    s.src = 'https://chat.example.com/widget.js';
    s.onload = function() { new TiledeskWindow({}); };
    d.head.appendChild(s);
  })(window, document);
</script>
```

---

## Head-to-Head Comparison

### Feature Coverage

| Capability | Chatwoot | Papercups | Tiledesk |
|------------|----------|-----------|----------|
| Website live chat | ✅ | ✅ | ✅ |
| Email inbox | ✅ | ❌ | ✅ |
| WhatsApp integration | ✅ | ❌ | ✅ |
| Facebook Messenger | ✅ | ❌ | ✅ |
| Twitter/X DMs | ✅ | ❌ | ❌ |
| Telegram | ✅ | ❌ | ✅ |
| SMS (via Twilio) | ✅ | ❌ | ❌ |
| Slack routing | ❌ | ✅ | ❌ |
| AI chatbot builder | ⚠️ Basic | ❌ | ✅ Advanced |
| Knowledge base | ✅ | ❌ | ✅ |
| Pre-chat forms | ✅ | ❌ | ✅ |
| Department routing | ⚠️ Basic | ❌ | ✅ |
| Canned responses | ✅ | ✅ | ✅ |
| File attachments | ✅ | ✅ | ✅ |
| Video chat | ❌ | ❌ | ❌ |
| Mobile apps | ✅ | ❌ | ✅ |
| Multi-brand / projects | ✅ | ❌ | ✅ |
| Analytics | ✅ Comprehensive | ⚠️ Basic | ✅ |
| GDPR compliance tools | ✅ | ✅ | ✅ |
| SSO / SAML | ⚠️ Enterprise | ❌ | ⚠️ Enterprise |
| REST API | ✅ | ✅ | ✅ |
| Webhooks | ✅ | ❌ | ✅ |
| Widget customization | ✅ Full | ⚠️ Limited | ✅ Full |

### Performance and Resources

| Metric | Chatwoot | Papercups | Tiledesk |
|--------|----------|-----------|----------|
| **Min RAM** | 1 GB | 256 MB | 512 MB |
| **CPU (light load)** | 0.5 cores | 0.1 cores | 0.3 cores |
| **Concurrent chats** | 5,000+ | 50,000+ | 10,000+ |
| **Database** | PostgreSQL | PostgreSQL | MongoDB |
| **Cache / Queue** | Redis (required) | None | None |
| **Docker images** | 2 services + deps | 1 service + DB | 2+ services + DB |
| **Cold start time** | ~30 seconds | ~5 seconds | ~15 seconds |
| **Horizontal scaling** | ✅ Multiple Rails instances | ✅ Phoenix clustering | ✅ Microservices |

### Maintenance Overhead

**Chatwoot** requires the most operational effort: Rails application server, PostgreSQL, Redis, and background workers. You need to manage database migrations, Redis persistence, and ensure the background job queue stays healthy. Updates are well-documented but require attention to version compatibility.

**Papercups** is the easiest to maintain: one application process and one database. Elixir's hot code reloading means zero-downtime deploys are straightforward. The smaller codebase means fewer things can break.

**Tiledesk** sits in the middle: Node.js is easy to deploy, but MongoDB requires regular backups and index management. The microservice architecture means more moving parts than Papercups but fewer than Chatwoot.

---

## Which One Should You Choose?

### Choose Chatwoot if:

- You need a complete customer engagement platform, not just live chat
- You want to consolidate email, social media, and website chat into one inbox
- Your team needs mobile apps for on-the-go support
- You want built-in knowledge base and workflow automation
- You have the infrastructure to support Rails + PostgreSQL + Redis

Chatwoot is the best choice for companies that want to replace Intercom entirely — live chat, email support, social media management, and a help center, all in one self-hosted platform.

### Choose Papercups if:

- You want the simplest possible live chat deployment
- You have limited server resources (a $5 VPS is enough)
- Your team lives in Slack and wants chat messages routed there
- You only need website live chat — no email, no social media
- You value raw performance and WebSocket reliability above all else

Papercups is the best choice for developers and small teams who want a "set it and forget it" live chat widget that just works.

### Choose Tiledesk if:

- You want AI-powered chatbots to handle the first line of support
- You need department-based routing for larger support teams
- You want pre-chat forms for lead qualification
- You need to manage multiple brands or websites from one installation
- You prefer Node.js and MongoDB over Ruby and PostgreSQL

Tiledesk is the best choice for organizations that want to automate repetitive support queries with chatbots while still providing seamless escalation to human agents.

---

## Deployment Tips for All Platforms

### 1. Always Use HTTPS

Live chat widgets are embedded on customer-facing websites. Running them over HTTP exposes every conversation to man-in-the-middle attacks. Use Caddy for automatic Let's Encrypt certificates, or configure Nginx with certbot.

### 2. Set Up Regular Backups

Your conversation history is valuable business data. Automate daily database dumps:

```bash
# PostgreSQL backup (Chatwoot, Papercups)
docker exec papercups-postgres pg_dump -U papercups papercups_prod \
  | gzip > /backups/papercups-$(date +%Y%m%d).sql.gz

# MongoDB backup (Tiledesk)
docker exec tiledesk-mongo mongodump \
  --username tiledesk --password ${MONGO_PASSWORD} \
  --archive=/backups/tiledesk-$(date +%Y%m%d).gz --gzip
```

### 3. Configure Email Delivery

All three platforms send email notifications — password resets, conversation alerts, and visitor follow-ups. Configure SMTP settings correctly, and consider using a transactional email service like Postmark or SendGrid for reliable delivery.

### 4. Monitor Resource Usage

Set up basic monitoring with Prometheus and node_exporter to track memory, CPU, and database connection pools. Chatwoot's Rails processes can grow under heavy load, while Papercups' Elixir BEAM VM is remarkably stable but benefits from tuning the scheduler count.

### 5. Widget Performance

Add `defer` or `async` to your widget script tags to avoid blocking page rendering. Set up a CDN for the widget JavaScript if your visitors are geographically distributed — even a self-hosted platform benefits from edge caching for static assets.

---

## Final Verdict

The self-hosted live chat landscape in 2026 offers genuine alternatives to expensive SaaS platforms. **Chatwoot** leads in feature completeness and is the closest thing to a drop-in Intercom replacement. **Papercups** wins on simplicity and performance — deploy it in five minutes and forget about it. **Tiledesk** brings AI-powered automation to the forefront, making it the smartest choice for teams drowning in repetitive support queries.

All three are open-source, free to self-host, and give you full ownership of your customer data. The decision comes down to your team's size, your technical capacity, and how you want to handle customer conversations.
