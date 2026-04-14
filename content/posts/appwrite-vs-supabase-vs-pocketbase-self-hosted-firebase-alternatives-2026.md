---
title: "Appwrite vs Supabase vs PocketBase: Best Self-Hosted Firebase Alternative 2026"
date: 2026-04-14
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Compare the top three self-hosted Backend-as-a-Service platforms — Appwrite, Supabase, and PocketBase — as open-source Firebase alternatives. Complete setup guides, feature comparison, and recommendations for 2026."
---

Firebase has long been the default choice for developers who want a ready-made backend: authentication, real-time databases, file storage, and cloud functions, all behind a single SDK. But Firebase comes with vendor lock-in, unpredictable pricing at scale, and data residency constraints that many organizations cannot accept.

In 2026, the self-hosted Backend-as-a-Service (BaaS) landscape has matured enough that you can replicate — and in many cases exceed — Firebase's feature set while keeping full control of your data, your infrastructure, and your budget.

## Why Self-Host Your Backend-as-a-Service

Running your own BaaS platform solves problems that hosted services create:

**Data sovereignty.** Your user data, files, and credentials never leave your servers. This is mandatory for healthcare (HIPAA), finance (PCI DSS, GDPR), and government workloads where third-party data processing is legally restricted.

**Cost predictability.** Firebase's pay-as-you-go pricing can spiral when your app hits scale. Reading 10 million documents per day or storing terabytes of files adds up fast. Self-hosted platforms run on fixed infrastructure costs — a $20/month VPS can handle thousands of users.

**No vendor lock-in.** When your backend runs on open-source software with standard protocols (PostgreSQL, REST APIs, WebSockets), you can migrate, fork, or extend it freely. You are not tied to a proprietary SDK or cloud ecosystem.

**Customization.** Need a custom authentication flow, a specialized database index, or a webhook that talks to your internal systems? Self-hosted platforms let you modify every layer.

**Offline and air-gapped deployments.** Some environments simply cannot reach the public internet. Self-hosted BaaS platforms work in isolated networks, on-premises data centers, and edge locations.

## Three Contenders

The self-hosted BaaS space has three dominant players, each with a different philosophy:

| Feature | **PocketBase** | **Appwrite** | **Supabase** |
|---------|---------------|--------------|--------------|
| **Language** | Go (embedded) | Node.js / Docker | PostgreSQL ecosystem |
| **Database** | SQLite (embedded) | MariaDB / MariaDB Galera | PostgreSQL |
| **Architecture** | Single binary | Microservices (10+ containers) | Managed PostgreSQL + edge functions |
| **Authentication** | Built-in (email, OAuth2, SAML) | Built-in (email, phone, OAuth2, SAML, magic URL) | Built-in (email, phone, OAuth2, SAML, magic URL, MFA) |
| **Real-time** | Server-Sent Events | Realtime subscriptions | PostgreSQL replication + WebSockets |
| **Storage** | Local disk / S3 | Appwrite Storage / S3 | Supabase Storage / S3 |
| **Server-side logic** | JavaScript hooks (embedded) | Cloud Functions (Deno) | Edge Functions (Deno) + Postgres functions |
| **Admin UI** | Built-in single-page app | Built-in comprehensive console | Built-in dashboard + Table editor |
| **Self-hosted difficulty** | Trivial | Moderate | Moderate |
| **Minimum RAM** | 64 MB | 2 GB | 2 GB |
| **GitHub Stars** | 43k+ | 45k+ | 70k+ |
| **License** | MIT | BSD-3-Clause | Apache 2.0 |

### PocketBase: The Minimalist

PocketBase is a single Go binary that bundles SQLite, a real-time subscription engine, an admin dashboard, and a file storage system. You download one file, run it, and you have a complete backend.

It is ideal for small to medium projects, internal tools, prototyping, and anyone who values simplicity over horizontal scale. The embedded SQLite database handles tens of thousands of concurrent users when configured correctly.

### Appwrite: The Full-Featured Platform

Appwrite is a Docker-based platform with 10+ microservices: API gateway, database, storage, users, functions, messaging, and more. It provides the broadest feature set of the three, including teams, project-level isolation, GraphQL support, and a comprehensive audit log.

It is the closest direct replacement for Firebase's feature parity and is suited for production applications that need enterprise-grade tooling.

### Supabase: The PostgreSQL Powerhouse

Supabase is built on top of PostgreSQL and leverages the database itself as the backend engine. Row-Level Security (RLS) policies control access, triggers power real-time events, and PostgREST auto-generates a REST API from your schema.

If you already know PostgreSQL, Supabase has the shallowest learning curve. The database is your API, and your API is the database.

## Installation and Setup

### PocketBase — Single Binary

PocketBase is the easiest to deploy. Download the binary and run:

```bash
# Download and extract
wget https://github.com/pocketbase/pocketbase/releases/download/v0.25.8/pocketbase_0.25.8_linux_amd64.zip
unzip pocketbase_0.25.8_linux_amd64.zip
chmod +x pocketbase

# Start the server
./pocketbase serve --http 0.0.0.0:8080
```

Create a systemd service for production:

```ini
# /etc/systemd/system/pocketbase.service
[Unit]
Description=PocketBase Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/pocketbase
ExecStart=/opt/pocketbase/pocketbase serve --http 0.0.0.0:8080
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable pocketbase
systemctl start pocketbase
```

Access the admin panel at `http://your-server:8080/_/` and create your first admin account.

For production with HTTPS behind Caddy:

```caddyfile
# Caddyfile
api.example.com {
    reverse_proxy localhost:8080
}
```

### Appwrite — Docker Compose

Appwrite ships as a multi-container Docker setup. The official installation script handles everything:

```bash
docker run -it --rm \
    --volume /var/run/docker.sock:/var/run/docker.sock \
    --volume "$(pwd)"/appwrite:/usr/src/code/appwrite:rw \
    --entrypoint="install" \
    appwrite/appwrite:1.7.0
```

Or use Docker Compose manually:

```yaml
# docker-compose.yml
version: '3.8'

services:
  appwrite:
    image: appwrite/appwrite:1.7.0
    container_name: appwrite
    restart: unless-stopped
    networks:
      - appwrite
    labels:
      - traefik.enable=true
      - traefik.http.routers.appwrite.rule=Host(`appwrite.example.com`)
      - traefik.http.routers.appwrite.entrypoints=websecure
      - traefik.http.routers.appwrite.tls.certresolver=letsencrypt
    volumes:
      - appwrite-uploads:/storage/uploads:rw
      - appwrite-cache:/storage/cache:rw
      - appwrite-config:/storage/config:rw
      - appwrite-certificates:/storage/certificates:rw
      - appwrite-functions:/storage/functions:rw
    depends_on:
      - mariadb
      - redis
    environment:
      - _APP_ENV=production
      - _APP_OPENSSL_KEY_V1=your-secret-key
      - _APP_DB_PASS=database-password
      - _APP_REDIS_PASS=redis-password

  mariadb:
    image: mariadb:10.11
    container_name: appwrite-mariadb
    restart: unless-stopped
    networks:
      - appwrite
    volumes:
      - appwrite-mariadb:/var/lib/mysql
    environment:
      - MYSQL_ROOT_PASSWORD=database-password

  redis:
    image: redis:7-alpine
    container_name: appwrite-redis
    restart: unless-stopped
    networks:
      - appwrite

volumes:
  appwrite-uploads:
  appwrite-cache:
  appwrite-config:
  appwrite-certificates:
  appwrite-functions:
  appwrite-mariadb:

networks:
  appwrite:
    driver: bridge
```

After deployment, access the Appwrite console at `http://your-server:80` and complete the setup wizard. The first run initializes the database schema and creates the admin account.

### Supabase — Docker Compose

Supabase provides an official Docker Compose setup via the `supabase` CLI:

```bash
# Install the CLI
curl -fsSL https://raw.githubusercontent.com/supabase/cli/main/install.sh | sh

# Initialize a new project
mkdir supabase-project && cd supabase-project
supabase init

# Start all services locally
supabase start
```

For a standalone Docker Compose deployment without the CLI:

```yaml
# docker-compose.yml
version: '3.8'

services:
  db:
    image: supabase/postgres:15.1.1.78
    container_name: supabase-db
    restart: unless-stopped
    ports:
      - "5432:5432"
    volumes:
      - db-data:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: your-super-secret-postgres-password
      JWT_SECRET: your-jwt-secret-at-least-32-chars
    healthcheck:
      test: pg_isready -U postgres
      interval: 10s
      timeout: 5s
      retries: 5

  kong:
    image: kong:2.8.1
    container_name: supabase-kong
    restart: unless-stopped
    ports:
      - "8000:8000"
      - "8443:8443"
    environment:
      KONG_DATABASE: "off"
      KONG_DECLARATIVE_CONFIG: /var/lib/kong/kong.yml
    volumes:
      - ./volumes/api/kong.yml:/var/lib/kong/kong.yml:ro

  auth:
    image: supabase/gotrue:v2.164.0
    container_name: supabase-auth
    restart: unless-stopped
    environment:
      GOTRUE_API_HOST: 0.0.0.0
      GOTRUE_DB_DATABASE_URL: postgres://postgres:your-super-secret-postgres-password@db:5432/postgres
      GOTRUE_JWT_SECRET: your-jwt-secret-at-least-32-chars
      GOTRUE_SITE_URL: http://localhost:3000
      GOTRUE_MAILER_AUTOCONFIRM: "true"

  rest:
    image: postgrest/postgrest:v12.2.0
    container_name: supabase-rest
    restart: unless-stopped
    environment:
      PGRST_DB_URI: postgres://postgres:your-super-secret-postgres-password@db:5432/postgres
      PGRST_JWT_SECRET: your-jwt-secret-at-least-32-chars
      PGRST_DB_SCHEMAS: public

  realtime:
    image: supabase/realtime:v2.33.45
    container_name: supabase-realtime
    restart: unless-stopped
    environment:
      DB_HOST: db
      DB_PORT: 5432
      DB_PASSWORD: your-super-secret-postgres-password

  storage:
    image: supabase/storage-api:v1.14.5
    container_name: supabase-storage
    restart: unless-stopped
    environment:
      POSTGREST_URL: http://rest:3000
      STORAGE_BACKEND: file
      FILE_STORAGE_BACKEND_PATH: /var/lib/storage
      GLOBAL_S3_BUCKET: local
    volumes:
      - storage-data:/var/lib/storage

volumes:
  db-data:
  storage-data:
```

The Supabase stack is more complex because each component is a separate service. The Kong API gateway routes requests, GoTrue handles authentication, PostgREST auto-generates the REST API from your Postgres schema, Realtime listens to database changes via PostgreSQL replication, and Storage manages file uploads.

## Authentication Deep Dive

Authentication is the most critical feature of any BaaS platform. Here is how the three compare:

| Auth Feature | PocketBase | Appwrite | Supabase |
|-------------|-----------|----------|----------|
| Email/Password | Yes | Yes | Yes |
| OAuth2 (Google, GitHub, etc.) | Yes (10+ providers) | Yes (15+ providers) | Yes (20+ providers) |
| Phone/SMS | No (requires hook) | Yes (Twilio, TextLocal, MSG91) | Yes (Twilio, MessageBird) |
| Magic Links | Yes | Yes | Yes |
| SAML/SSO | Yes (paid plans in cloud) | Yes (self-hosted) | Yes (enterprise in cloud) |
| Multi-factor Auth (MFA) | Via hook | Built-in (TOTP) | Built-in (TOTP, SMS) |
| Anonymous Auth | Yes | Yes | Yes |
| JWT Custom Claims | Yes | Yes (via functions) | Yes (via Postgres triggers) |
| Session Management | Built-in | Built-in with device tracking | Built-in with refresh tokens |
| Password Reset | Built-in email | Built-in email + phone | Built-in email |

All three support email confirmation, password reset flows, and OAuth2 out of the box. Appwrite and Supabase have more identity providers and native SMS support. PocketBase can integrate any OAuth2 provider through its extensible auth hooks.

## Database and API

### PocketBase

PocketBase uses SQLite with a built-in ORM and a reactive REST API. You define collections (tables) through the admin UI or via JavaScript migrations:

```javascript
// migrations/1680000000_create_posts.js
migrate((db) => {
  const collection = new Collection({
    name: "posts",
    type: "base",
    schema: [
      { name: "title", type: "text", required: true },
      { name: "body", type: "editor", required: true },
      { name: "author", type: "relation", required: true, options: { collectionId: "users" } },
      { name: "published", type: "bool", default: false },
    ],
    listRule: "published = true",
    viewRule: "published = true || author.id = @request.auth.id",
    createRule: "@request.auth.id != '' && author.id = @request.auth.id",
    updateRule: "author.id = @request.auth.id",
    deleteRule: "@request.auth.id = author.id",
  });

  return db.save(collection);
});
```

The `listRule`, `viewRule`, `createRule`, `updateRule`, and `deleteRule` fields provide declarative, row-level access control. Every request is evaluated against these rules before data is returned.

API usage:

```bash
# List published posts
curl http://localhost:8080/api/collections/posts/records?filter=published=true

# Create a post (authenticated)
curl -X POST http://localhost:8080/api/collections/posts/records \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Hello World","body":"Content here"}'
```

### Appwrite

Appwrite provides a REST API, GraphQL API, and official SDKs for web, Flutter, React Native, and server-side languages. Databases are organized into databases → collections → documents:

```javascript
// Using the Appwrite Web SDK
import { Client, Databases, ID } from 'appwrite';

const client = new Client()
  .setEndpoint('https://appwrite.example.com/v1')
  .setProject('your-project-id');

const databases = new Databases(client);

// Create a document
const doc = await databases.createDocument(
  'my-database',
  'posts',
  ID.unique(),
  {
    title: 'Hello World',
    body: 'Content here',
    published: true,
  },
  ['role:all'] // permissions
);

// Query with filters
const results = await databases.listDocuments(
  'my-database',
  'posts',
  [
    Query.equal('published', true),
    Query.orderDesc('$createdAt'),
    Query.limit(10),
  ]
);
```

Appwrite's permission model uses role strings (`role:all`, `user:{userId}`, `team:{teamId}`) that can be attached at the document level for fine-grained access control.

### Supabase

Supabase exposes your PostgreSQL schema as a REST API through PostgREST. You define tables with standard SQL, and the API appears automatically:

```sql
-- Create a table with Row-Level Security
CREATE TABLE posts (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  title text NOT NULL,
  body text NOT NULL,
  author_id uuid REFERENCES auth.users(id),
  published boolean DEFAULT false,
  created_at timestamptz DEFAULT now()
);

-- Enable Row-Level Security
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;

-- Policy: anyone can read published posts
CREATE POLICY "Published posts are viewable by everyone"
  ON posts FOR SELECT
  USING (published = true);

-- Policy: authors can insert their own posts
CREATE POLICY "Authors can create posts"
  ON posts FOR INSERT
  WITH CHECK (auth.uid() = author_id);

-- Policy: authors can update their own posts
CREATE POLICY "Authors can update their own posts"
  ON posts FOR UPDATE
  USING (auth.uid() = author_id);
```

API usage:

```bash
# List published posts
curl "http://localhost:8000/rest/v1/posts?published=eq.true&order=created_at.desc&limit=10" \
  -H "apikey: YOUR_ANON_KEY"

# Create a post (authenticated)
curl -X POST "http://localhost:8000/rest/v1/posts" \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Authorization: Bearer USER_JWT" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  -d '{"title":"Hello World","body":"Content here","author_id":"uuid-here"}'
```

The advantage of Supabase's approach is that you get the full power of PostgreSQL: complex joins, full-text search, geospatial queries (via PostGIS), materialized views, and stored procedures.

## Real-Time Subscriptions

All three platforms support real-time data synchronization:

**PocketBase** uses Server-Sent Events (SSE) through a simple subscribe endpoint:

```javascript
import PocketBase from 'pocketbase';
const pb = new PocketBase('http://localhost:8080');

pb.collection('posts').subscribe('*', (data) => {
  console.log('Real-time update:', data.record);
}, { expand: 'author' });
```

**Appwrite** uses WebSocket-based channels:

```javascript
import { Client, Realtime } from 'appwrite';

const realtime = new Realtime(client);

realtime.subscribe(['databases.my-database.collections.posts.documents'], (response) => {
  console.log('Real-time event:', response.payload);
});
```

**Supabase** listens directly to PostgreSQL replication events:

```javascript
import { createClient } from '@supabase/supabase-js';
const supabase = createClient('http://localhost:8000', 'YOUR_ANON_KEY');

supabase
  .channel('posts-changes')
  .on('postgres_changes', { event: '*', schema: 'public', table: 'posts' }, (payload) => {
    console.log('Change received:', payload);
  })
  .subscribe();
```

Supabase's approach is unique because it reads from PostgreSQL's Write-Ahead Log (WAL), meaning real-time events fire for any database change — even those made through direct SQL, psql, or other database clients.

## Server-Side Functions

When client-side logic is not enough, all three platforms offer server-side execution:

### PocketBase — JavaScript Hooks

PocketBase runs embedded JavaScript hooks inside the same process:

```javascript
// hooks.js
onRecordAfterCreateRequest((e) => {
  const record = e.record;
  console.log('New post created:', record.get('title'));

  // Send email notification, trigger webhook, etc.
  const mailer = $app.newMail();
  mailer.to = 'admin@example.com';
  mailer.subject = 'New post: ' + record.get('title');
  $app.send(mailer);
}, 'posts');
```

### Appwrite — Cloud Functions

Appwrite deploys functions as isolated Docker containers:

```javascript
// functions/hello-world/index.js
export default async ({ req, res, log, error }) => {
  log('Incoming request:', req.body);

  const payload = { response: 'Hello from Appwrite Functions!' };

  return res.json(payload, 200, {
    'Content-Type': 'application/json',
  });
};
```

Functions are triggered by HTTP requests, scheduled cron jobs, or database events. Appwrite supports Deno, Node.js, Python, PHP, Ruby, Go, Dart, C#, Kotlin, Swift, and Bun runtimes.

### Supabase — Edge Functions

Supabase runs Deno-based edge functions:

```typescript
// supabase/functions/hello/index.ts
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';

serve(async (req) => {
  const { name } = await req.json();

  return new Response(
    JSON.stringify({ message: `Hello, ${name}!` }),
    { headers: { 'Content-Type': 'application/json' } }
  );
});
```

Deploy with:

```bash
supabase functions deploy hello --project-ref your-project-ref
```

## Performance and Scalability

The architectural differences between these platforms produce very different scaling characteristics:

| Metric | PocketBase | Appwrite | Supabase |
|--------|-----------|----------|----------|
| **Cold start** | Instant (single binary) | ~15 seconds (Docker compose) | ~30 seconds (full stack) |
| **Read throughput** | ~10k req/s (single node) | ~5k req/s (single node) | ~8k req/s (single node) |
| **Write throughput** | Limited by SQLite WAL | Good (MariaDB cluster) | Excellent (PostgreSQL) |
| **Horizontal scaling** | Read replicas only | Full microservice scaling | PostgreSQL read replicas + connection pooling |
| **Max concurrent connections** | ~10k (SQLite) | ~5k (per node) | ~200 (without PgBouncer), unlimited (with PgBouncer) |
| **Memory footprint** | ~30 MB idle | ~800 MB idle | ~600 MB idle |

PocketBase is the most resource-efficient by a large margin. A Raspberry Pi can run PocketBase for a small project. Appwrite and Supabase need a minimum of 2 GB RAM and benefit from multi-core servers.

For horizontal scaling, Supabase and Appwrite both support read replicas and connection pooling. PocketBase can use Litestream for SQLite replication to a read-only replica, but write scaling requires application-level sharding.

## Backup and Disaster Recovery

### PocketBase

PocketBase is a single directory. Backing up means copying the data directory:

```bash
# Manual backup
cp -r /opt/pocketbase/pb_data /backups/pb_data_$(date +%F)

# Litestream replication to S3
litestream replicate -config /etc/litestream.yml /opt/pocketbase/pb_data/data.db
```

### Appwrite

Appwrite volumes need consistent backups:

```bash
# Backup MariaDB
docker exec appwrite-mariadb mysqldump -u root -p'${MYSQL_ROOT_PASSWORD}' --all-databases > backup.sql

# Backup volumes
docker run --rm -v appwrite-uploads:/data -v $(pwd):/backup alpine tar czf /backup/appwrite-uploads.tar.gz -C /data .
```

### Supabase

PostgreSQL has mature backup tooling:

```bash
# Logical backup
docker exec supabase-db pg_dump -U postgres -F c -f /var/lib/postgresql/backup/full.dump

# Point-in-time recovery with WAL-G
docker exec supabase-db wal-g backup-push /var/lib/postgresql/data
```

## Which One Should You Choose?

**Choose PocketBase if:**
- You are building a personal project, internal tool, or MVP
- You want zero operational overhead — one binary, done
- Your project fits comfortably within SQLite's concurrency model (read-heavy workloads)
- You value simplicity and want to manage less infrastructure

**Choose Appwrite if:**
- You need the widest feature set — teams, GraphQL, audit logs, messaging, AV generation
- You are migrating from Firebase and want the closest API parity
- You need multi-tenant project isolation (one Appwrite instance, many projects)
- Your team is comfortable with Docker and container orchestration

**Choose Supabase if:**
- Your application is data-heavy and benefits from PostgreSQL's features (joins, full-text search, PostGIS, window functions)
- You want the flexibility of standard SQL for complex queries
- You plan to scale horizontally with read replicas and connection pooling
- You already use PostgreSQL and want a seamless integration

## Getting Started Today

The fastest way to evaluate any of these platforms is to spin them up locally:

```bash
# PocketBase — download, extract, run
curl -fsSL https://github.com/pocketbase/pocketbase/releases/latest/download/pocketbase_linux_amd64 -o pocketbase
chmod +x pocketbase && ./pocketbase serve

# Appwrite — one command
docker run -it --rm --volume /var/run/docker.sock:/var/run/docker.sock --volume "$(pwd)"/appwrite:/usr/src/code/appwrite:rw --entrypoint="install" appwrite/appwrite:latest

# Supabase — CLI based
npx supabase init && npx supabase start
```

All three are production-ready, actively maintained, and backed by vibrant open-source communities. The best choice depends on your project's scale, your team's expertise, and your infrastructure preferences. What they all share is something Firebase cannot offer: your data stays on your servers, under your control, forever.
