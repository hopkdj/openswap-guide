---
title: "Self-Hosted Citizen Participation & E-Democracy Platforms: Decidim vs Consul Democracy vs Polis"
date: "2026-06-08"
tags: ["citizen-participation", "e-democracy", "open-government", "civic-tech", "consensus", "community-engagement", "self-hosted"]
draft: false
---

## Introduction

Democratic participation doesn't stop at the ballot box. Municipal governments, advocacy organizations, cooperatives, and community groups increasingly need digital platforms where citizens can propose ideas, deliberate on policies, participate in participatory budgeting, and reach consensus on collective decisions. While commercial "civic engagement" platforms exist, they come with significant costs, vendor lock-in, and privacy concerns when citizen data flows through third-party servers.

Self-hosted e-democracy platforms put control back in the hands of the community. Running your own participation platform means citizen data stays on your infrastructure, platform rules reflect your governance model rather than a vendor's business model, and the software itself can be adapted to your specific democratic processes — whether that's a neighborhood association voting on park improvements or a city government running a participatory budget cycle.

This guide compares three leading open-source citizen participation platforms: **Decidim** (full-featured participatory democracy framework), **Consul Democracy** (government-focused e-participation), and **Polis** (large-scale deliberation and consensus mapping).

## Why Self-Host Your Civic Participation Platform?

Trust is the foundation of democratic participation. When citizens contribute ideas, vote on budget allocations, or deliberate on policy proposals, they need confidence that the platform is fair, transparent, and immune to manipulation. A self-hosted platform makes this trust verifiable — the source code is open for audit, the database can be backed up independently, and the platform's administrators are accountable to the community, not a distant SaaS company.

Cost is another factor. Commercial civic engagement platforms charge per-user fees that scale with participation — exactly the opposite of what you want. A self-hosted open-source platform costs the same whether 100 or 100,000 citizens participate, removing the financial disincentive to broad engagement.

If your organization is also exploring secure online voting, see our comparison of [self-hosted online voting platforms](../2026-06-04-self-hosted-online-voting-helios-electionguard-belenios-guide/). For managing member relationships alongside civic participation, our [nonprofit CRM and association management guide](../2026-06-04-self-hosted-nonprofit-crm-association-civicrm-tendenci-guide/) covers complementary tools.

## Comparison Table

| Feature | Decidim | Consul Democracy | Polis |
|---------|---------|-----------------|-------|
| **Primary Focus** | Participatory democracy (proposals, budgets, assemblies) | Government e-participation (debates, proposals, voting) | Large-scale deliberation & consensus mapping |
| **Deployment Scale** | City-level to national | City government focused | Any scale (10 to 100,000+ participants) |
| **Proposal System** | Full proposal lifecycle with amendments | Citizen proposals with supports | Open-ended statements (not formal proposals) |
| **Participatory Budgeting** | Built-in (budget allocation with geolocation) | Budget investments module | Not applicable |
| **Deliberation Method** | Structured debates and assemblies | Comment-based debates | Statistical consensus detection |
| **Architecture** | Ruby on Rails monolith | Ruby on Rails | Node.js + PostgreSQL |
| **Docker Support** | docker-compose (official) | docker-compose | docker-compose |
| **GitHub Stars** | 1,763+ | 1,533+ | 1,174+ |
| **License** | AGPLv3 | AGPLv3 | AGPLv3 |
| **Multilingual** | 50+ languages | 30+ languages | 20+ languages |

## Decidim: The Full Participatory Democracy Suite

Decidim (Catalan for "we decide") is the most comprehensive platform in this comparison. Originally developed for the Barcelona City Council, it has since been adopted by cities including Helsinki, Mexico City, and New York, as well as organizations like the French National Assembly and the UN Development Programme.

### Key Features

- **Proposals**: Citizens submit, debate, and amend proposals. Proposals collect supports (endorsements) and progress through configurable workflows
- **Participatory Budgeting**: Define budget amounts, let citizens propose and vote on spending projects, with geolocation-aware allocation
- **Assemblies**: Structured deliberative bodies with membership, meeting scheduling, and minute-taking
- **Consultations**: Run referendums and surveys with multiple question types
- **Initiatives**: Grassroots petition system where citizens gather signatures to trigger official responses
- **Accountability**: Track the status of accepted proposals from approval through implementation

### Deployment

```bash
# Clone and deploy with Docker
git clone https://github.com/decidim/decidim.git
cd decidim

# Configure environment
cp .env.example .env
# Edit .env with your domain, SMTP settings, and database credentials

# Start the stack
docker-compose up -d

# Create admin user
docker-compose exec app bundle exec rails decidim:create_admin
```

### Docker Compose Architecture

```yaml
# Production docker-compose.yml
version: '3'
services:
  app:
    image: decidim/decidim:0.28
    environment:
      - DATABASE_URL=postgresql://decidim:password@db/decidim
      - REDIS_URL=redis://redis:6379/0
      - RAILS_ENV=production
      - SECRET_KEY_BASE=${SECRET_KEY_BASE}
      - SMTP_ADDRESS=${SMTP_ADDRESS}
    volumes:
      - ./storage:/app/storage
      - ./public/uploads:/app/public/uploads
    depends_on:
      - db
      - redis
    ports:
      - "3000:3000"

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=decidim
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  sidekiq:
    image: decidim/decidim:0.28
    command: bundle exec sidekiq
    environment:
      - DATABASE_URL=postgresql://decidim:password@db/decidim
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

volumes:
  pgdata:
```

## Consul Democracy: Government-Built for Governments

Consul Democracy (formerly Consul Project) was developed by the Madrid City Council and has been deployed by over 130 institutions worldwide, primarily city governments. Its design philosophy centers on the specific needs of public administrations: legal compliance, accessibility, transparency, and integration with government systems.

### Key Features

- **Debates**: Structured discussion spaces organized by topic with moderation tools
- **Proposals**: Citizen proposals that advance to voting when they reach support thresholds
- **Participatory Budgeting**: Georeferenced budget allocation with project costing and feasibility analysis
- **Voting**: Secure voting on proposals with verification codes
- **Legislation**: Collaborative drafting of laws and regulations with version tracking
- **Admin Dashboard**: Comprehensive moderation, statistics, and configuration interface

### Quick Deployment

```bash
# Clone and deploy
git clone https://github.com/consul/consul.git
cd consul

# Copy config files
cp config/database.yml.example config/database.yml
cp config/secrets.yml.example config/secrets.yml

# Docker deployment
docker-compose up -d

# Create admin user
docker-compose exec app bundle exec rake db:seed
```

### Nginx Reverse Proxy Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name participate.yourcity.gov;

    ssl_certificate /etc/letsencrypt/live/participate.yourcity.gov/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/participate.yourcity.gov/privkey.pem;

    # Security headers for government sites
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Cache static assets
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff2)$ {
        proxy_pass http://127.0.0.1:3000;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

## Polis: Large-Scale Deliberation Through Statistics

Polis takes a fundamentally different approach to citizen participation. Rather than structured proposals and voting, it enables open-ended deliberation where participants write short statements, vote on others' statements (agree/disagree/pass), and a statistical engine identifies clusters of opinion and areas of consensus.

### Key Features

- **Open-ended participation**: No predefined agenda — participants contribute whatever statements they consider relevant
- **Real-time visualization**: Opinion groups emerge visually as people vote, showing where consensus exists and where views diverge
- **Bridging statements**: The system automatically identifies statements that receive broad agreement across opinion groups — powerful for finding common ground
- **Scale independence**: Works equally well for a neighborhood meeting (50 people) or a national conversation (100,000+)
- **Moderation toolkit**: Flag inappropriate content, manage participant access, and configure conversation parameters

### Deployment

```bash
# Clone the repository
git clone https://github.com/compdemocracy/polis.git
cd polis

# Configure environment
cp example.env .env
# Edit .env with domain, database, and email settings

# Deploy with Docker
docker-compose up -d

# The platform will be available at http://localhost:5000
```

### Polis Docker Compose

```yaml
version: '3'
services:
  polis-server:
    image: compdem/polis-server:latest
    environment:
      - DATABASE_URL=postgres://polis:${DB_PASSWORD}@db/polis
      - PORT=5000
    ports:
      - "5000:5000"
    depends_on:
      - db

  polis-math:
    image: compdem/polis-math:latest
    environment:
      - DATABASE_URL=postgres://polis:${DB_PASSWORD}@db/polis
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=polis
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=polis
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

## Choosing the Right Platform

- **Full participatory democracy suite**: If your organization needs proposals, participatory budgeting, assemblies, and accountability tracking — essentially a complete digital democracy infrastructure — **Decidim** is the clear choice. Its feature breadth is unmatched, though the initial configuration requires dedicated administrative effort.

- **Government-specific e-participation**: If you're a city government that needs a platform purpose-built for public administration workflows — with legal compliance features, accessibility standards, and official integration capabilities — **Consul Democracy** has been battle-tested by over 130 governments.

- **Large-scale deliberation and consensus building**: If your goal is understanding what a community thinks rather than running formal voting processes, **Polis** offers a unique approach. Its statistical consensus detection reveals where agreement exists even across polarized groups — making it especially valuable for divisive topics where traditional voting would only highlight conflict.

The three platforms can also complement each other: use Polis for initial community exploration of a topic, Decidim for the formal proposal and budgeting process, and Consul for the official government integration layer.

## FAQ

### Can I run these platforms for a small neighborhood association with just 50 members?

Yes. All three platforms scale down to small groups. For a neighborhood association, Decidim's assemblies feature is particularly well-suited — you can create an assembly for your neighborhood, set up proposal and debate components, and manage membership. The Docker Compose setups above run comfortably on a $20/month VPS with 2GB RAM.

### How do these platforms handle accessibility requirements for government use?

Both Decidim and Consul Democracy have undergone accessibility audits and comply with WCAG 2.1 AA standards. Consul, in particular, emphasizes accessibility given its government deployment focus — it supports screen readers, keyboard navigation, and high-contrast modes. Polis has a simpler interface that is naturally accessible but hasn't undergone formal WCAG certification.

### What happens if someone tries to manipulate a participatory budgeting vote?

Decidim and Consul both include verification mechanisms: unique voting codes distributed through official channels (SMS, postal mail), one-vote-per-verified-user enforcement, and audit trails. These are not cryptographic end-to-end verifiable voting systems (for that, see our voting platforms guide), but they provide sufficient integrity for participatory budgeting where the stakes are lower than binding elections.

### Can I customize the look and feel to match my city's branding?

Yes. All three platforms support custom themes. Decidim has an admin interface for basic customization (colors, logos, homepage layout). Consul allows full CSS customization and template overrides. Polis supports custom CSS injection and can be embedded as an iframe within an existing municipal website with matching branding.

### How do I migrate from a commercial civic engagement platform to an open-source one?

Data migration depends on what your existing platform exports. Decidim provides API endpoints and import scripts for proposals and users. Consul has rake tasks for bulk data import from CSV. The main migration work is typically in data mapping (matching your existing data schema to the new platform's models) rather than technical import. Budget 2-4 weeks for a typical city-scale migration, including data cleaning and user communication.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Citizen Participation & E-Democracy Platforms: Decidim vs Consul Democracy vs Polis",
  "description": "Comprehensive comparison of open-source citizen participation platforms for self-hosted e-democracy. Covers Decidim, Consul Democracy, and Polis with Docker deployment, Nginx configuration, and platform selection guidance for governments and community organizations.",
  "datePublished": "2026-06-08",
  "dateModified": "2026-06-08",
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
